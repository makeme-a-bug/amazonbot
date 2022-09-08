import random
import time
from typing import Dict,List,Any,Union
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException , NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC


from .utils import solve_captch
from rich.console import Console


# reviews are inside id profile-at-card-container
# each review div has class profile-at-card
# the link to review is profile-at-review-link

class Reporter(webdriver.Remote):

    def __init__(self,profile_name:str,profile_uuid:str, urls:List[str], command_executor:str, destroy_browser:bool = True , tracker:List = [] ) -> None:
        self.command_executor = command_executor
        # self.capabilities = desired_capabilities
        self.profile_name = profile_name
        self.profile_uuid = profile_uuid
        self.urls = urls
        self.destroy_browser = destroy_browser
        self.console = Console()
        self.tracker = tracker

        super(Reporter,self).__init__(self.command_executor,desired_capabilities={})
        self.set_page_load_timeout(120)
        self.implicitly_wait(120)



    def gather_reviews(self):
        for url in self.urls:
            self.tracker.append({
                'profile':self.profile_name,
                'exists':True,
                'url':url
            })
            if self.get_page(url):
                captcha = self.solve_captcha()
                logged_in = self.is_profile_logged_in()
                time.sleep(2)
                self.tracker[-1]['captcha_solved'] = captcha
                self.tracker[-1]['Logged_in'] = logged_in
                if captcha and logged_in:
                    self.move_mouse_around(3)
                    time.sleep(2)
                    reviews = self.get_reviews()
                    time.sleep(2)
                    self.start_reporting(reviews)
                elif not logged_in:
                    break
                else:
                    continue
        self.quit()
                    


    def get_reviews(self) -> List[str]:
        """
        Gets first six reviews from buyer profile
        """
        reviews_div = self.find_element(By.ID,'profile-at-card-container') #div that contains all the reviews
        reviews = reviews_div.find_elements(By.CLASS_NAME,'profile-at-card')[:6] # get first 6 reviews
        urls = []
        for r in reviews:
            url = r.find_element(By.CSS_SELECTOR,"a.profile-at-review-link")
            url = url.get_attribute("href").replace("https://www.amazon.com","")
            urls.append(url)
        self.console.log(f"Profile [{self.profile_name}] Found {len(urls)} reviews to be reported",style="blue")
        self.tracker[-1]['reviews_found'] = len(urls)
        return urls



    def get_review_page(self,url:str) -> bool:
        """
        Opens review page by finding the url and clicking on it \n
        Parameter: \n
        url:<str> \n
        return: \n
        True: if url was opened \n
        False: if url was not opened \n
        """
        actions = ActionChains(self) 
        try:
            ele = self.find_element(By.CSS_SELECTOR,f"a[href='{url}']")
            actions.move_to_element(ele).pause(2).click().perform()
            time.sleep(2)
            self.console.log(f"review page opened",style="blue")
            return True
        except NoSuchElementException as e:
            self.console.log(f"div for url {url} not found",style="red")
        return False

    def go_back(self) -> None:
        """
        goes back one page
        """
        self.implicitly_wait(20)
        reviews_div = self.find_elements(By.ID,'profile-at-card-container')
        self.implicitly_wait(120)
        if reviews_div:
            return

        self.execute_script("window.history.go(-1)")
        try:
            _ = WebDriverWait(self, 120).until(EC.presence_of_element_located((By.ID,'profile-at-card-container')))
        except:
            pass



    def start_reporting(self,urls:List[str]) -> None:
        """
        Starts reporting for the review urls \n
        Parameters: \n
        urls: list<str> : review urls \n
        returns: \n
        None \n
        """
        abuse_buttons_clicked = 0
        for url in urls:
            time.sleep(5)
            if self.get_review_page(url):
                captcha = self.solve_captcha()
                if captcha:
                    self.move_mouse_around()
                    time.sleep(2)
                    clicked = self.click_abuse_button()
                    if clicked:
                        abuse_buttons_clicked += 1
                        time.sleep(2)
                        self.go_back()
                    time.sleep(2)
                else:
                    time.sleep(2)
                    continue
        self.tracker[-1]['reviews_reported'] = abuse_buttons_clicked            

    def get_page(self,url:str) -> bool:
        """
        gets the url in the browser.\n
        parameters:\n
        url:<str>
        returns:\n
        None
        """
        found = False
        attempt = 0
        while not found and attempt < 2:
            self.get(url)
            try:
                _ = WebDriverWait(self, 120).until(EC.element_to_be_clickable((By.ID,"nav-logo")))
                found = True
                return True
            except TimeoutException as e:
                self.console.log("Page took too long load.",style="red")
                self.console.log("Trying again" , style="blue")
                attempt += 1
        return False



    def solve_captcha(self) -> bool:
        """
        Checks if captcha appreared on the page.if appeared will try to solve it.
        return:
        True  : if captcha was solved
        False : if captcha was not solved
        """

        if "Try different image" in self.page_source:
            print(f"Captcha appear for profile [{self.profile_uuid}]")
            if not solve_captch(self):
                print(self.profile_name, "CAPTCHA not solved")
                return False
        return True


    
    def is_profile_logged_in(self) -> bool:
        """
        Checks if the multilogin is logged into amazon \n
        returns:\n
        True  : if the profile is logged in
        False : if the profile is not logged in
        """

        if self.find_elements(By.CSS_SELECTOR, 'a[data-csa-c-content-id="nav_youraccount_btn"]'):
            return True
        self.console.log(f"{self.profile_name}:Profile not logged in into Amazon account",style='red')
        return False



    def click_abuse_button(self) -> bool:
        """
        Clicks abuse button for the review.
        """

        abuse_btns = self.find_elements(By.CSS_SELECTOR, "a.report-abuse-link")
        actions = ActionChains(self) 
        if abuse_btns:
            actions.move_to_element(abuse_btns[0]).pause(2).click().perform()
            report_window = None
            main_window = self.current_window_handle
            #when clicked on abuse button it opens a new tab
            #so we try to find the popup window
            for window in self.window_handles:
                if window != main_window:
                    report_window = window

            if report_window:
                self.switch_to_window(report_window)
                #sometime captcha appears
                captcha = self.solve_captcha()
                if captcha:
                    report_button = self.find_element(By.CSS_SELECTOR,'a[data-hook="cr-report-abuse-pop-over-button"]')
                    if report_button:
                        time.sleep(2)
                        report_button.click()
                        self.console.log(f"[{self.profile_name}] [Report abuse ] button clicked" , style="blue")
                        time.sleep(3)
                        self.close()
                        self.switch_to_window(main_window)
                        return True

                    self.console.log("report button not found",style="red")
                else:
                    self.console.log("CAPTCHA not solved for report button popup",style="red")

            return False
            
        else:
            print(f"[{self.profile_name}] Abuse button not found")
            return False




    def move_mouse_around(self,num_ele:int = 5):
        """
        moves mouse arounds the screen in random pattern.
        """
        elements = self.find_elements(By.CSS_SELECTOR,'a')
        actions = ActionChains(self)
        length_of_elements = len(elements)
        if elements:
            for _ in range(length_of_elements if length_of_elements <= num_ele else num_ele):
                try:
                    move_to = random.choice(elements)
                    self.execute_script("arguments[0].scrollIntoView(true);", move_to)
                    actions.move_to_element(random.choice(elements)).pause(2).perform()
                    time.sleep(4)
                    actions.reset_actions()
                except:
                    pass
        time.sleep(2)

       

    def bring_inside_viewport(self,selector:str='[id^=CardInstance]'):
        """
        brings a element to the center of viewport
        """
        recommendations = self.find_element(By.CSS_SELECTOR,selector)
        if recommendations:
            desired_y = (recommendations.size['height'] / 2) + recommendations.location['y']
            window_h = self.execute_script('return window.innerHeight')
            window_y = self.execute_script('return window.pageYOffset')
            current_y = (window_h / 2) + window_y
            scroll_y_by = desired_y - current_y
            self.execute_script("window.scrollBy(0, arguments[0]);", scroll_y_by)




    def __exit__(self, *args) -> None:
        if self.destroy_browser:
            self.quit()


