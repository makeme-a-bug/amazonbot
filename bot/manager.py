from typing import Dict,List,Any,Union
import requests
import pandas as pd
from .reporter import Reporter
from rich.console import Console

class ReporterManager:
    
    def __init__(self,file:str="inputs/report_abuse_input.csv" , port:int = 35000):
        
        self.file = file
        self.port = port
        self.console = Console()
        self.profiles = self.getProfiles()
        self.inputs = self.getInput()
        self.create_reporters()
        
    
    def getProfiles(self) -> Union[Dict,None]:
        """
        Get all profiles from multilogin
        """
        try:
            url = f'http://localhost:{self.port}/api/v2/profile'
            profiles = requests.get(url)
            profiles = profiles.json()
            profiles_map = {}
            for r in profiles:
                profiles_map[r['name']] = r['uuid']

            return profiles_map

        except requests.exceptions.Timeout:
            self.console.log(f"Request to get profiles timeout",style="red")
            return

        except requests.exceptions.ConnectionError as e:
            self.console.log(f"Please make sure multilogin API is running. Failed to make request to the API.",style="red")
            raise SystemExit()

        except requests.exceptions as e:
            self.console.log("Request failed due to",style="red")
            print(e)
            return

        
    
    def getInput(self) -> pd.DataFrame:
        """
        reads the report_abuse_input.csv
        """
        df = pd.read_csv(self.file)
        df.sort_values(["Profile"],inplace=True)
        return df
        
        
    
    def start_profile_browser(self, profile_id:str) -> Union[str, None]:
        """
            Starts browser profile for given profile_id        
        """
        try:
            mla_url = (
                f"http://127.0.0.1:{self.port}/api/v1/profile/start?automation=true&profileId=" + profile_id
            )
            resp = requests.get(mla_url)
            json:Dict = resp.json()
            if resp.status_code == 500:
                self.console.log(f"profile with id:{profile_id} not found",style="red")
                return
            

        except requests.exceptions.Timeout:
            self.console.log(f"Request to get profile:{profile_id} timeout",style="red")
            return

        except requests.exceptions.ConnectionError as e:
            self.console.log(f"Please make sure multilogin API is running. Failed to make request to the API.",style="red")
            raise SystemExit()

        except requests.exceptions as e:
            self.console.log("Request failed due to",style="red")
            print(e)
            return
        
        return json.get('value',None)

            
    
    def create_reporters(self):
        with self.console.status("[bold green]Working on tasks...") as status:
            profiles = []
            for profile_name in self.inputs.Profile.unique():
                profile_uuid:str = self.profiles.get(profile_name,None)
                if not profile_uuid:
                    self.console.log(f"profile not found:{profile_name}",style='red')
                    profiles.append({
                        'profile':profile_name,
                        'exists':False,
                    })
                    continue

                urls:List[str] = self.inputs[self.inputs['Profile'] == profile_name]['Buyer Account URL'].tolist()

                mla_url = self.start_profile_browser(profile_uuid)
                if not mla_url:
                    continue
                    
                with Reporter(profile_name , profile_uuid , urls , mla_url,tracker = profiles) as R:
                    R.gather_reviews()

                self.console.log(f"{profile_name} reporting complete",style='green')
            tracker = pd.DataFrame(profiles)
            tracker.to_csv('report.csv')
                