import pytest
import allure
import time
import json
from loguru import logger

from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.common.exceptions import ElementNotInteractableException
from selenium.common.exceptions import TimeoutException
from allure_commons.types import AttachmentType
from urllib.parse import urlparse
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


class Component:

    def __init__(self, locator, desc=None):
        self.locator = locator
        self.desc = locator[1] if desc == None else desc


@pytest.mark.usefixtures("driver_init")
class BaseHandler:
    timeout = 5

    def __init__(self) -> None:
        options = Options()
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9527")
        self.driver = webdriver.Chrome(options=options)
        self.url = self.driver.current_url
        print(self.url)

    def quit(self):
        self.driver.quit()

    def switch_to_default_content(self):
        self.driver.switch_to.default_content()

    def switch_to_iframe(self, loc, native=True):
        if native:
            self.switch_to_default_content()
        iframe = self.find_element(loc)
        self.driver.switch_to.frame(iframe)

    def switch_to_alert_and_accept(self):
        try:
            alert = WebDriverWait(self.driver, 15).until(EC.alert_is_present())
            alert.accept()
        except:
            logger.error("Alert is not found.")
            pass

    def __iswebelement(self, loc):
        return isinstance(loc, EC.WebElement)

    def find_element(self, loc, *args, **kargs):
        if self.__iswebelement(loc):
            return loc
        try:
            return WebDriverWait(self.driver, self.timeout, 1).until(EC.presence_of_element_located(loc.locator))
        except (NoSuchElementException, TimeoutException):
            logger.warning(f"{loc.desc} element is not found")
            self.screenshot(name=f"{loc.desc} element is not found")
            raise NoSuchElementException(f"' {loc.desc} ' element is not found. ")

    def find_elements(self, loc, wait=True, *args, **kwargs):
        if self.__iswebelement(loc):
            return loc
        try:
            if wait:
                return WebDriverWait(self.driver, self.timeout, 1).until(EC.presence_of_all_elements_located(loc.locator))
            return self.driver.find_elements(*loc.locator)
        except (NoSuchElementException, TimeoutException):
            logger.warning(f"{loc.desc} element is not found")
            self.screenshot(name=f"{loc.desc} element is not found")
            raise NoSuchElementException(f"' {loc.desc} ' element is not found. ")

    def wait_for_attribute_to_be_removed(self, loc, attribute, timeout=10):
        def _check_attribute_removed(driver):
            return self.get_attribute(loc=loc, attri=attribute) is None

        WebDriverWait(self.driver, timeout).until(_check_attribute_removed)

    def wait_for_element(self, loc, child_loc=None, wait_type="presence", timeout=None, poll_frequency=0.5):
        """
        Waits for a specific condition to be met for an element or elements.

        :param loc: The locator or WebElement to wait for.
        :param wait_type: The type of wait condition to apply. Supported values are:
        - "presence_all": Wait for all elements matching the locator to be present in the DOM.
        - "presence": Wait for a single element matching the locator to be present in the DOM.
        - "visibility": Wait for a single element matching the locator to be visible.
        - "visibility_all": Wait for all elements matching the locator to be visible.
        - "visibility_any": Wait for at least one element matching the locator to be visible.
        - "invisible": Wait for the element matching the locator to become invisible.
        - "clickable": Wait for the element matching the locator to be clickable.
        - "visibility_of": Wait for a WebElement to be visible (only for WebElements, not locators).

        :param timeout: The maximum time to wait for the condition to be met. Defaults to the class-level `timeout` attribute if not provided.
        :param poll_frequency: The frequency (in seconds) with which to poll for the condition. Default is 1 second.
        :return: The WebElement or a list of WebElements that meet the condition.
        """
        if timeout is None:
            timeout = self.timeout
        wait_conditions = {
            "presence_all": EC.presence_of_all_elements_located,  # For locator only. -> return list
            "presence": EC.presence_of_element_located,  # For locator only.
            "visibility": EC.visibility_of_element_located,  # For locator only.
            "visibility_all": EC.visibility_of_all_elements_located,  # For locator only. -> return list
            "visibility_any": EC.visibility_of_any_elements_located,  # For locator only. -> return list
            "invisible": EC.invisibility_of_element_located,  # For locator only.
            "clickable": EC.element_to_be_clickable,  # For locator and Webelement.
            "visibility_of": EC.visibility_of,  # For WebElements only
        }
        if wait_type not in wait_conditions:
            raise ValueError(f"Invalid wait_type: {wait_type}. Supported types are: {', '.join(wait_conditions.keys())}")
        wait_condition = wait_conditions[wait_type]
        self.web_wait()
        try:
            ele = loc.locator if not self.__iswebelement(loc) else loc
            name = loc.desc if not self.__iswebelement(loc) else loc.text.split("\n")[0]
            if child_loc:
                ele = self.find_element(loc=loc) if not self.__iswebelement(loc) else loc
                return WebDriverWait(ele, timeout, poll_frequency).until(wait_condition(child_loc.locator))
            return WebDriverWait(self.driver, timeout, poll_frequency).until(wait_condition(ele))
        except TimeoutException:
            logger.warning(f"'{name}' element is not found")
            self.screenshot(name=f"element is not found '{name}'")
            raise TimeoutException(f"Element not found for WebElement {name} and {child_loc} after {timeout} seconds")
        except Exception as e:
            error_msg = f"Wait for element exception error '{name}': {str(e)}"
            logger.error(error_msg)

    def find_child_element(self, loc, child_loc, *args, **kwargs):
        ele = self.find_element(loc=loc)
        try:
            return WebDriverWait(ele, self.timeout, 1).until(EC.presence_of_element_located(child_loc.locator))
        except:
            self.screenshot(name=f"element is not found {child_loc.desc}")
            raise NoSuchElementException(f"' {child_loc.desc} ' element is not found. ")

    def find_child_elements(self, loc, child_loc, *args, **kwargs):
        ele = self.find_element(loc=loc)
        try:
            return WebDriverWait(ele, self.timeout, 1).until(EC.presence_of_all_elements_located(child_loc.locator))
        except:
            self.screenshot(name=f"element is not found: {child_loc.desc}")
            raise NoSuchElementException(f"' {child_loc.desc} ' element is not found. ")

    def is_visiable(self, loc, *args, **kargs):
        if self.__iswebelement(loc):
            return loc.is_displayed()
        else:
            try:
                return self.find_element(loc=loc).is_displayed()
            except:
                self.screenshot(name=f"{loc.desc} element is not found")
                raise NoSuchElementException(f"' {loc.desc} ' element is not found. ")

    def move_to_element(self, loc):
        ele = self.find_element(loc=loc)
        if ele == None:
            return
        hover_element = ActionChains(self.driver).move_to_element(ele)
        hover_element.perform()

    def scroll_to_view(self, loc):
        ele = self.find_element(loc=loc) if not self.__iswebelement(loc=loc) else loc
        self.exec_js(js_string="arguments[0].scrollIntoView();", element=ele)
        return ele

    def element_invisible(self, loc):
        if self.__iswebelement(loc):
            return loc
        try:
            return WebDriverWait(self.driver).until(EC.invisibility_of_element_located(loc.locator))
        except:
            return False

    def get_attribute(self, loc, attri=None):
        ele = self.find_element(loc=loc)
        if ele == None:
            return
        attribute = ele.get_attribute(attri)
        print(attribute)
        return attribute

    def get_element_text(self, loc):
        try:
            text = loc.text if self.__iswebelement(loc=loc) else self.find_element(loc=loc).text
            return text
        except StaleElementReferenceException:
            return ""

    def input(self, loc, value):
        ele = self.find_element(loc=loc)
        try:
            if ele.text != "":
                ele.clear()
            ele.send_keys(value)
        except:
            ActionChains(self.driver).move_to_element(ele).send_keys(value).perform()

    def action_click(self, loc):
        ele = self.wait_for_element(loc=loc, timeout=1) if not self.__iswebelement(loc=loc) else loc
        print(ele)
        if ele == None:
            return
        ActionChains(self.driver).move_to_element(ele).click().perform()

    def click(self, loc, x=None, y=None, msg=None, srcoll=False):
        ele = self.wait_for_element(loc=loc, timeout=1) if not self.__iswebelement(loc=loc) else loc
        if ele == None:
            return
        if x == None and y == None:
            try:
                msg = msg if msg else self.get_element_text(ele)
                msg = "NoText" if not msg else msg
                with allure.step(f"Click : {msg}"):
                    if srcoll:
                        self.scroll_to_view(loc=ele)
                    ele.click()
                    logger.debug(f"Click : {msg}")
            except (ElementClickInterceptedException, ElementNotInteractableException):
                logger.warning(f"Element '{msg}' was intercepted - handled by Actionchains class")
                ActionChains(self.driver).move_to_element(ele).click().perform()
            except Exception as e:
                logger.warning(f"Click function error : {e}")
        elif x != None and y != None:
            ActionChains(self.driver).move_to_element_with_offset(ele, x, y).click().perform()

    def double_click(self, loc, x=None, y=None):
        ele = self.find_element(loc=loc)
        if ele == None:
            return
        if x == None and y == None:
            try:
                ele.double_click()
            except:
                ActionChains(self.driver).move_to_element(ele).double_click().perform()
        elif x != None and y != None:
            ActionChains(self.driver).move_to_element_with_offset(ele, x, y).double_click().perform()

    def spin(self, loc, x=None, y=None):
        ele = self.find_element(loc=loc)
        if ele == None:
            return
        btn = ActionChains(self.driver).move_to_element_with_offset(ele, x, y)
        btn.double_click()
        btn.perform()

    def keyboard(self, key):
        actions = ActionChains(self.driver)
        if key == "enter":
            actions.send_keys(Keys.ENTER)
        elif key == "tab":
            actions.send_keys(Keys.TAB)
        elif key == "home":
            actions.send_keys(Keys.HOME)
        elif key == "esc":
            actions.send_keys(Keys.ESCAPE)
        actions.perform()
        self.time_sleep(0.5)

    def open_url(self, url):
        self.driver.get(url=url)
        self.web_wait()
        return self.get_current_url()

    def get_current_url(self):
        self.web_wait()
        url = self.driver.current_url
        with allure.step(f"Get current url {url}"):
            return url

    def get_coordinates(self, loc):
        ele = self.find_element(loc=loc)
        locate = ele.location
        size = ele.size
        return locate, size

    def time_sleep(self, seconds):
        time.sleep(seconds)
        logger.debug(f"time sleep {seconds} seconds... ")

    def back_to_page(self):
        self.driver.back()

    def refresh_page(self):
        self.driver.refresh()
        self.web_wait()

    def assertion(self, expr, screen_shot=True, msg="", **kwargs):
        ret = pytest.assume(expr, msg)
        if kwargs:
            kwargs_str = json.dumps(kwargs, indent=2)
            allure.attach(body=str(kwargs_str), name=msg, attachment_type=AttachmentType.TEXT)
        result = "[FAIlDED]" if not expr else "[PASSED]"
        with allure.step(result + msg):
            if not expr:
                logger.error(f"Verify : {msg}")
                self.screenshot(name=f"{result + msg}")
                return None
            logger.success(f"Verify : {msg}")
            if screen_shot:
                self.screenshot(name=result + msg)
            return None

    def exec_js(self, js_string, element=None):
        if element:
            self.driver.execute_script(js_string, element)
        else:
            self.driver.execute_script(js_string)

    def screenshot(self, name):
        with allure.step(name):
            allure.attach(body=self.driver.get_screenshot_as_png(), name=name, attachment_type=AttachmentType.PNG)

    def web_wait(self):
        return WebDriverWait(self.driver, self.timeout).until(
            lambda d: d.execute_script("return document.readyState === 'complete' && document.body.innerHTML.trim().length > 0;")
        )

    def get_domain_url(self, url):
        if not url.startswith(("http://", "https://")):
            return url
        parsed_url = urlparse(url)
        domain_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        return domain_url
