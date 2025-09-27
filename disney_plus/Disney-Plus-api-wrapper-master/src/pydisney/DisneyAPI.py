import logging
import json # Add this import
import requests
from typing import Optional, List

from .Auth import Auth
from .Config import APIConfig
from .models.Account import Account
from .models.Hit import Hit
from .models.Profile import Profile
from .models.ProgramType import MovieType, SeriesType
from .utils.parser import parse_profile

# Create a custom logger
logger = logging.getLogger("pydisney")
logger.setLevel(logging.INFO)

# Create a console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # Set handler level to DEBUG

# Define a formatter and attach it to the handler
formatter = logging.Formatter("%(levelname)s: %(name)s: %(message)s")
console_handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(console_handler)


class DisneyAPI:
    def __init__(self, email: str, password: str, force_login: bool = False):

        self._auth = Auth(email=email, password=password, force_login=force_login)
        self._auth.get_auth_token()

        self.device_id = None
        self.device_platform = None
        self.sessions_id = None

        self.account: Optional[Account] = None
        self._account_init()
        self._session_init()

        APIConfig.region = "en" if self.account is None else self.account.country
        APIConfig.language = APIConfig.region

    def search(self, query: str) -> List[Hit]:
        res = Auth.make_pagination_request("GET", f"https://disney.api.edge.bamgrid.com/explore/v1.7/search?query={query}")
        for page in res:
            items = page["data"]["page"]["containers"]
            if not items:
                return []
            items = items[0]["items"]

            search_items = []
            for data in items:
                search_items.append(Hit(data))
            return search_items

    def _get_set(self, set_id) -> List[Hit]:
        url = f"https://disney.api.edge.bamgrid.com/explore/v1.7/set/{set_id}"
        res = Auth.make_pagination_request("GET", url)
        hits = []
        for page in res:
            items = page["data"]["set"]["items"]
            hits.extend(Hit.parse_hits(items))
        return hits

    def get_originals(self) -> List[Hit]:
        return self._get_set("3e935bc6-4984-4c49-acd8-a12a2e91ff40")

    def get_movies(self, movie_type: MovieType) -> List[Hit]:
        hits = self._get_set(movie_type.value)
        for hit in hits:
            hit.__is_movie = False
        return hits

    def get_series(self, series_type: SeriesType) -> List[Hit]:
        hits = self._get_set(series_type.value)
        for hit in hits:
            hit.__is_movie = False
        return hits

    def set_download_path(self, path: str) -> None:
        APIConfig.default_path = path

    def get_profiles(self) -> List[Profile]:
        graphql_query = {
            "query": """
                query {
                    me {
                        account {
                            profiles {
                                ...profile
                            }
                        }
                    }
                }
                fragment profile on Profile {
                    id
                    name
                    attributes {
                        avatar {
                            id
                            userSelected
                        }
                        isDefault
                        kidsModeEnabled
                        languagePreferences {
                            appLanguage
                            playbackLanguage
                            subtitleLanguage
                            subtitlesEnabled
                        }
                    }

                }
            """,
            "variables": {}
        }
        res = Auth.make_request("POST", "https://disney.api.edge.bamgrid.com/v1/public/graphql", data=graphql_query)

        profiles = []
        for profile in res["data"]["me"]["account"]["profiles"]:
            profiles.append(parse_profile(profile))
        return profiles

    def get_active_profile(self) -> Profile:
        graphql_query = {
            "query": """
                query {
                    me {
                        account {
                            activeProfile {
                                ...profile
                            }
                        }
                    }
                }
                fragment profile on Profile {
                    id
                    name
                    attributes {
                        avatar {
                            id
                            userSelected
                        }
                        isDefault
                        kidsModeEnabled
                        languagePreferences {
                            playbackLanguage
                            subtitleLanguage
                            subtitlesEnabled
                            appLanguage
                        }
                    }
                }
            """,
            "variables": {}
        }
        res = Auth.make_request("POST", "https://disney.api.edge.bamgrid.com/v1/public/graphql", data=graphql_query)
        profile = res["data"]["me"]["account"]["activeProfile"]
        return parse_profile(profile)

    def set_active_profile(self, profile_id: str, pin: str = None) -> None:
        access_token, refresh_token = self._auth.set_active_profile(APIConfig.token, profile_id, pin)
        APIConfig.token = access_token
        APIConfig.refresh = refresh_token

    def _account_init(self):
        graphql_query = {
            "query": """
                query {
                    me {
                        account {
                            ...account
                        }
                    }
                }
                fragment account on Account {
                    id
                    attributes {
                        consentPreferences {
                            dataElements {
                                name
                                value
                            }
                        }
                        dssIdentityCreatedAt
                        email
                        emailVerified
                        userVerified
                    }
                }
            """,
            "variables": {}
        }

        res = Auth.make_request("POST", "https://disney.api.edge.bamgrid.com/v1/public/graphql", data=graphql_query)

        acc_json = res["data"]["me"]["account"]
        account_id = acc_json["id"]
        email = acc_json["attributes"]["email"]
        email_verified = acc_json["attributes"]["emailVerified"]
        created_at = acc_json["attributes"]["dssIdentityCreatedAt"]
        try:
            country = acc_json["attributes"]["consentPreferences"]["dataElements"][0]["value"]
        except IndexError:
            # country seems to be missing for newly create accounts
            country = "en"
            logger.warning("Couldn't set country, fallback to default: EN-gb")

        account = Account(account_id=account_id, email=email, created_at=created_at, country=country,
                          is_email_verified=email_verified)
        self.account = account

    def _session_init(self):
        graphql_query = {
            "query": """
                query {
                    me {
                        activeSession {
                            ...session
                        }
                    }
                }
                fragment session on Session {
                     device {
                        id
                     platform
                     }
                    sessionId
                }
            """,
            "variables": {}
        }
        res = Auth.make_request("POST", "https://disney.api.edge.bamgrid.com/v1/public/graphql", data=graphql_query)

        sess_json = res["data"]["me"]["activeSession"]
        APIConfig.sessionId = sess_json["sessionId"]
        self.device_id = sess_json["device"]["id"]
        self.device_platform = sess_json["device"]["platform"]

    def get_token(self) -> str:
        return APIConfig.token

    def set_log_level(self, level: int) -> None:
        logger.setLevel(level)
        console_handler.setLevel(level)


    def get_user_content_state(self, pids: List[str]) -> dict:
        """
        Fetches the user's viewing state (progress, etc.) for a list of content PIDs.
        Args:
            pids: A list of content PIDs (program IDs) to query the state for.
        Returns:
            A dictionary containing the user's content state for the given PIDs.
        """
        url = "https://disney.api.edge.bamgrid.com/explore/v1.10/userState"
        
        # Prepare the request body with PIDs (as used by browser)
        body = {
            "pids": pids
        }
        
        # Headers matching exactly what the browser sends
        headers = {
            "Content-Type": "application/json",
            "accept": "application/json",
            "authorization": f"Bearer {APIConfig.token}",  # Add auth manually
            "x-application-version": "1.1.2",
            "x-bamsdk-client-id": "disney-svod-3d9324fc",
            "x-bamsdk-platform": "javascript/chromium/edge",
            "x-bamsdk-version": "32.6",
            "x-dss-edge-accept": "vnd.dss.edge+json; version=2",
            "origin": "https://www.disneyplus.com",
            "referer": "https://www.disneyplus.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0"
        }
        
        logger.info(f"Requesting user state for {len(pids)} PIDs via POST")
        logger.info(f"Request URL: {url}")
        #logger.info(f"Request body: {json.dumps(body)}")
        
        # Make the request directly with requests to avoid header conflicts
        response = requests.post(url, json=body, headers=headers)
        
        if not response.ok:
            logger.error(f"User state request failed: {response.status_code} - {response.text}")
            raise Exception(f"User state API failed: {response.status_code} - {response.text}")
        
        return response.json()

    def get_watchlist_set(self, set_id):
        """
        Fetch the user's watchlist set from Disney+ API with fixed parameters.
        """
        url = (
            f"https://disney.api.edge.bamgrid.com/explore/v1.10/set/{set_id}"
            "?layoutId=6efe57d7-a01a-4c76-ac9c-ed69ede33e9c"
            "&limit=48"
            "&offset=0"
            "&pageId=f58fe84b-f2b6-4948-947d-e0721aeacad0"
            "&pageStyle=standard_emphasis_with_navigation"
            "&setResolutionId=5ddf0f81-2085-42b5-8e49-1088e9573563"
            "&setStyle=standard_art"
        )
        res = Auth.make_request("GET", url)
        return res

    def get_watchlist_items(self, set_id):
        """
        Get list of shows/movies from watchlist.
        Returns the items array from the watchlist set.
        """
        watchlist = self.get_watchlist_set(set_id)
        return watchlist["data"]["set"]["items"]

    def get_entity_details(self, entity_id):
        """
        Get detailed page for a show/movie entity.
        Returns the full entity page with episodes, personalization PIDs, etc.
        """
        url = (
            f"https://disney.api.edge.bamgrid.com/explore/v1.10/page/entity-{entity_id}"
            "?disableSmartFocus=true"
            "&enhancedContainersLimit=15"
            "&limit=15"
        )
        res = Auth.make_request("GET", url)
        return res

    def get_season_episodes(self, season_id):
        """
        Get episodes for a specific season.
        """
        url = f"https://disney.api.edge.bamgrid.com/explore/v1.7/season/{season_id}"
        res = Auth.make_request("GET", url)  # Use make_request instead of make_pagination_request
        
        # The response structure for season endpoint is different
        season_data = res["data"]["season"]
        episodes = season_data.get("items", [])
        
        return episodes

    def get_watchlist_progress(self, set_id):
        """
        High-level method: Get watchlist with user progress for all shows/movies/episodes.
        Returns a list of dicts with show info, episode info, and user progress.
        """
        # 1. Get watchlist items
        items = self.get_watchlist_items(set_id)
        
        all_pids = []
        pid_to_info = {}
        
        # 2. For each item, get entity details and extract PIDs
        for item in items:
            entity_id = item["id"]
            show_title = item["visuals"]["title"]
            
            try:
                entity_details = self.get_entity_details(entity_id)
                
                # Infer entity type since params.entity_type is not always present
                containers = entity_details["data"]["page"]["containers"]
                entity_type = "movie"  # default
                
                # Look for episodes container to identify series
                for container in containers:
                    if container["type"] == "episodes":
                        entity_type = "series"
                        break
                
                if entity_type == "series":
                    # Handle TV shows with seasons and episodes
                    for container in containers:
                        if container["type"] == "episodes":
                            for season in container.get("seasons", []):
                                season_id = season["id"]
                                season_name = season.get("visuals", {}).get("name", f"Season {len(container.get('seasons', [])) + 1}")
                                
                                # Check if this season has episodes loaded
                                season_episodes = season.get("items", [])
                                
                                # Always try to fetch episodes for each season using the season API
                                # This ensures we get all episodes from all seasons, not just the default one
                                if not season_episodes:
                                    try:
                                        season_episodes = self.get_season_episodes(season_id)
                                    except Exception as e:
                                        logger.warning(f"Failed to load episodes for season {season_id} ({season_name}): {e}")
                                        continue
                                
                                # Process episodes
                                for episode in season_episodes:
                                    pid = episode.get("personalization", {}).get("pid")
                                    if pid:
                                        all_pids.append(pid)
                                        pid_to_info[pid] = {
                                            "entity_type": "series",
                                            "show_title": show_title,
                                            "season_name": season_name,
                                            "seasonNumber": episode["visuals"].get("seasonNumber"),
                                            "episodeNumber": episode["visuals"].get("episodeNumber"),
                                            "fullEpisodeTitle": episode["visuals"].get("fullEpisodeTitle"),
                                            "episodeTitle": episode["visuals"].get("episodeTitle"),
                                            "durationMs": episode["visuals"].get("durationMs"),
                                            "personalization_pid": pid,
                                            "progressPercentage": None,
                                            "secondsRemaining": None,
                                        }
                
                elif entity_type == "movie":
                    # Handle movies - look for PID in the page data
                    page_pid = entity_details["data"]["page"].get("personalization", {}).get("pid")
                    if page_pid:
                        all_pids.append(page_pid)
                        # Get movie duration from details container
                        movie_duration = None
                        for container in containers:
                            if container["type"] == "details":
                                movie_duration = container["visuals"].get("duration", {}).get("runtimeMs")
                                break
                        
                        pid_to_info[page_pid] = {
                            "entity_type": "movie",
                            "show_title": show_title,
                            "season_name": None,
                            "seasonNumber": None,
                            "episodeNumber": None,
                            "fullEpisodeTitle": None,
                            "episodeTitle": None,
                            "durationMs": movie_duration,
                            "personalization_pid": page_pid,
                            "progressPercentage": None,
                            "secondsRemaining": None,
                        }
            except Exception as e:
                logger.warning(f"Failed to get entity details for {show_title}: {e}")
                continue
        
        # 3. Batch fetch user state for all PIDs
        if all_pids:
            try:
                user_states = self.get_user_content_state(all_pids)
                states = user_states.get("data", {}).get("entityStates", {})
                
                # 4. Merge progress info
                for pid, state in states.items():
                    progress = state.get("progress", {})
                    if pid in pid_to_info:
                        pid_to_info[pid]["progressPercentage"] = progress.get("progressPercentage")
                        pid_to_info[pid]["secondsRemaining"] = progress.get("secondsRemaining")
            except Exception as e:
                logger.warning(f"Failed to get user state: {e}")
        
        # 5. Return list of all items with progress
        return list(pid_to_info.values())