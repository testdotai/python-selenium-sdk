import base64
import hashlib
import json
import logging
import os
import platform
import requests
import sys
import time
import traceback
import urllib.parse
import uuid
import warnings
import webbrowser


import io
from distutils.util import strtobool
from PIL import Image
from packaging import version
import selenium

if version.parse(selenium.__version__) < version.parse('4.0.0'):
    old_selenium = True
else:
    old_selenium = False

from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import StaleElementReferenceException

from selenium import webdriver

requests.packages.urllib3.disable_warnings()


log = logging.getLogger(__name__)

class TestAiDriver():
    def __init__(self, driver, api_key, test_case_name=None, debug=False, use_classifier_during_creation=True,
                 train=False, server_url=None, use_cdp=False):
        self.version = 'selenium-0.1.20'
        self.debug = debug
        self.train = train
        self.driver = driver
        self.api_key = api_key
        self.run_id = str(uuid.uuid1())
        self.last_test_case_screenshot_uuid = None
        self.use_cdp = use_cdp
        try:
            self.test_case_creation_mode = strtobool(os.environ.get('TESTAI_INTERACTIVE', '0')) == 1
        except Exception:
            self.test_case_creation_mode = False
        if test_case_name is None:
            test_case_name = traceback.format_stack()[0].split()[1].split('/')[-1].split('.py')[0]
        self.test_case_uuid = test_case_name
        if self.test_case_creation_mode:
            self.use_classifier_during_creation = use_classifier_during_creation
        if server_url is None:
            server_url = os.environ.get('TESTAI_FLUFFY_DRAGON_URL', 'https://sdk.test.ai')
        self.url = server_url
        self._checkin()
        window_size = self.driver.get_window_size()
        screenshotBase64 = self._get_screenshot()

        im = Image.open(io.BytesIO(base64.b64decode(screenshotBase64)))
        width, height = im.size
        self.multiplier = 1.0 * width / window_size['width']
        self_attrs = dir(self)
        # Disable warnings
        requests.packages.urllib3.disable_warnings()
        warnings.filterwarnings("ignore", category=DeprecationWarning)

        for a_name in dir(driver):
            if a_name in self_attrs:
                continue
            try:
                def _call_driver(*args, name=a_name, **kwargs):
                    v = getattr(self.driver, name)
                    return v(*args, **kwargs)
                v = getattr(self.driver, a_name)
                if hasattr(v, '__call__'):
                    setattr(self, a_name, _call_driver)
                else:
                    setattr(self, a_name, v)
            except Exception as err:
                continue

    def get(self, url):
        self.driver.get(url)
        for a_name in dir(self.driver):
            try:
                v = getattr(self.driver, a_name)
                if hasattr(v, '__call__'):
                    continue
                elif '__' == a_name[0:2]:
                    # Skip these as they mess with internal properties
                    continue
                else:
                    setattr(self, a_name, v)
            except Exception as err:
                continue


    def implicitly_wait(self, wait_time):
        self.driver.implicitly_wait(wait_time)


    def find_element(self, by='id', value=None, element_name=None):
        """
        Find an element given a By strategy and locator.
        :Usage:
            ::
                element = driver.find_element(By.ID, 'foo')
        :rtype: WebElement
        """

        # Try to classify with selector
        #    If success, call update_elem ('train_if_necessary': true)
        #    If NOT successful, call _classify
        #        If succesful, return element
        #        If NOT succesful, raise element not found with link
        if element_name is None:
            element_name = 'element_name_by_%s_%s' % (str(by).replace('.', '_'), str(value).replace('.', '_'))
        element_name = element_name.replace(' ', '_')
        key = None
        msg = 'test.ai driver exception'

        # Run the standard selector
        try:
            driver_element = self.driver.find_element(by=by, value=value)
            if driver_element:
                key = self._upload_screenshot_if_necessary(element_name)
                self._update_elem(driver_element, key, element_name)
            return driver_element
        except NoElementFoundException as e:
            log.exception(e)
        except Exception:
            # If this happens, then error during the driver call
            classified_element, key, msg = self._classify(element_name)
            if classified_element:
                log.error('Selector failed, using test.ai classifier element')
                return classified_element
            else:
                raise Exception(msg)
        return None

    def find_element_by_accessibility_id(self, accessibility_id, element_name=None):
        """
        Finds an element by an accessibility id.

        :Args:
         - accessibility_id: The name of the element to find.
         - element_name: The label name of the element to be classified.

        :Returns:
         - WebElement - the element if it was found

        :Raises:
         - NoSuchElementException - if the element wasn't found

        :Usage:
            ::
                element = driver.find_element_by_accessibility_id('foo')
        """
        if element_name is None:
            element_name = 'element_name_by_accessibility_id_%s' % (str(accessibility_id).replace('.', '_'))
        element_name = element_name.replace(' ', '_')

        key = None
        msg = 'test.ai driver exception'

        # Run the standard selector
        try:
            driver_element = self.driver.find_element_by_accessibility_id(accessibility_id)
            if driver_element:
                key = self._upload_screenshot_if_necessary(element_name)
                self._update_elem(driver_element, key, element_name)
            return driver_element
        except NoElementFoundException as e:
            log.exception(e)
        except Exception as err:
            # If this happens, then error during the driver call
            classified_element, key, msg = self._classify(element_name)
            if classified_element:
                log.error('Selector failed, using test.ai classifier element')
                return classified_element
            else:
                raise Exception(msg)
        return None

    def find_element_by_class_name(self, name, element_name=None):
        """
        Finds an element by class name.

        :Args:
         - name: The class name of the element to find.
         - element_name: The label name of the element to be classified.

        :Returns:
         - WebElement - the element if it was found

        :Raises:
         - NoSuchElementException - if the element wasn't found

        :Usage:
            ::
                element = driver.find_element_by_class_name('foo')
        """
        if element_name is None:
            element_name = 'element_name_by_class_name_%s' % (str(name).replace('.', '_'))
        element_name = element_name.replace(' ', '_')

        key = None
        msg = 'test.ai driver exception'

        # Run the standard selector
        try:
            driver_element = self.driver.find_element_by_class_name(name)
            if driver_element:
                key = self._upload_screenshot_if_necessary(element_name)
                self._update_elem(driver_element, key, element_name)
            return driver_element
        except NoElementFoundException as e:
            log.exception(e)
        except Exception as err:
            # If this happens, then error during the driver call
            classified_element, key, msg = self._classify(element_name)
            if classified_element:
                log.error('Selector failed, using test.ai classifier element')
                return classified_element
            else:
                raise Exception(msg)
        return None


    def find_element_by_css_selector(self, css_selector, element_name=None):
        """
        Finds an element by css selector.

        :Args:
         - css_selector - CSS selector string, ex: 'a.nav#home'
         - element_name: The label name of the element to be classified.

        :Returns:
         - WebElement - the element if it was found

        :Raises:
         - NoSuchElementException - if the element wasn't found

        :Usage:
            ::

                element = driver.find_element_by_css_selector('#foo')
        """
        if element_name is None:
            element_name = 'element_name_by_css_selector_%s' % (str(css_selector).replace('.', '_'))
        element_name = element_name.replace(' ', '_')

        key = None
        msg = 'test.ai driver exception'

        # Run the standard selector
        try:
            driver_element = self.driver.find_element_by_css_selector(css_selector)
            if driver_element:
                key = self._upload_screenshot_if_necessary(element_name)
                self._update_elem(driver_element, key, element_name)
            return driver_element
        except NoElementFoundException as e:
            log.exception(e)
        except Exception as err:
            # If this happens, then error during the driver call
            classified_element, key, msg = self._classify(element_name)
            if classified_element:
                log.error('Selector failed, using test.ai classifier element')
                return classified_element
            else:
                raise Exception(msg)
        return None


    def find_element_by_id(self, id_, element_name=None):
        """
        Finds an element by id.

        :Args:
         - id\\_ - The id of the element to be found.
         - element_name: The label name of the element to be classified.

        :Returns:
         - WebElement - the element if it was found

        :Raises:
         - NoSuchElementException - if the element wasn't found

        :Usage:
            ::

                element = driver.find_element_by_id('foo')
        """
        if element_name is None:
            element_name = 'element_name_by_id_%s' % (str(id_).replace('.', '_'))
        element_name = element_name.replace(' ', '_')

        key = None
        msg = 'test.ai driver exception'

        # Run the standard selector
        try:
            driver_element = self.driver.find_element_by_id(id_)
            if driver_element:
                key = self._upload_screenshot_if_necessary(element_name)
                self._update_elem(driver_element, key, element_name)
            return driver_element
        except NoElementFoundException as e:
            log.exception(e)
        except Exception as err:
            # If this happens, then error during the driver call
            classified_element, key, msg = self._classify(element_name)
            if classified_element:
                log.error('Selector failed, using test.ai classifier element')
                return classified_element
            else:
                raise Exception(msg)
        return None


    def find_element_by_link_text(self, link_text, element_name=None):
        """
        Finds an element by link text.

        :Args:
         - link_text: The text of the element to be found.
         - element_name: The label name of the element to be classified.

        :Returns:
         - WebElement - the element if it was found

        :Raises:
         - NoSuchElementException - if the element wasn't found

        :Usage:
            ::

                element = driver.find_element_by_link_text('Sign In')
        """
        if element_name is None:
            element_name = 'element_name_by_link_text_%s' % (str(link_text).replace('.', '_'))
        element_name = element_name.replace(' ', '_')

        key = None
        msg = 'test.ai driver exception'

        # Run the standard selector
        try:
            driver_element = self.driver.find_element_by_link_text(link_text)
            if driver_element:
                key = self._upload_screenshot_if_necessary(element_name)
                self._update_elem(driver_element, key, element_name)
            return driver_element
        except NoElementFoundException as e:
            log.exception(e)
        except Exception as err:
            # If this happens, then error during the driver call
            classified_element, key, msg = self._classify(element_name)
            if classified_element:
                log.error('Selector failed, using test.ai classifier element')
                return classified_element
            else:
                raise Exception(msg)
        return None


    def find_element_by_name(self, name, element_name=None):
        """
        Finds an element by name.

        :Args:
         - name: The name of the element to find.
         - element_name: The label name of the element to be classified.

        :Returns:
         - WebElement - the element if it was found

        :Raises:
         - NoSuchElementException - if the element wasn't found

        :Usage:
            ::

                element = driver.find_element_by_name('foo')
        """
        if element_name is None:
            element_name = 'element_name_by_name_%s' % (str(name).replace('.', '_'))
        element_name = element_name.replace(' ', '_')

        key = None
        msg = 'test.ai driver exception'


        # Run the standard selector
        try:
            driver_element = self.driver.find_element_by_name(name)
            if driver_element:
                key = self._upload_screenshot_if_necessary(element_name)
                self._update_elem(driver_element, key, element_name)
            return driver_element
        except NoElementFoundException as e:
            log.exception(e)
        except Exception as err:
            # If this happens, then error during the driver call
            classified_element, key, msg = self._classify(element_name)
            if classified_element:
                log.error('Selector failed, using test.ai classifier element')
                return classified_element
            else:
                raise Exception(msg)
        return None


    def find_element_by_partial_link_text(self, link_text, element_name=None):
        """
        Finds an element by a partial match of its link text.

        :Args:
         - link_text: The text of the element to partially match on.
         - element_name: The label name of the element to be classified.

        :Returns:
         - WebElement - the element if it was found

        :Raises:
         - NoSuchElementException - if the element wasn't found

        :Usage:
            ::

                element = driver.find_element_by_partial_link_text('Sign')
        """
        if element_name is None:
            element_name = 'element_name_by_partial_link_text_%s' % (str(link_text).replace('.', '_'))
        element_name = element_name.replace(' ', '_')

        key = None
        msg = 'test.ai driver exception'

        # Run the standard selector
        try:
            driver_element = self.driver.find_element_by_partial_link_text(link_text)
            if driver_element:
                key = self._upload_screenshot_if_necessary(element_name)
                self._update_elem(driver_element, key, element_name)
            return driver_element
        except NoElementFoundException as e:
            log.exception(e)
        except Exception as err:
            # If this happens, then error during the driver call
            classified_element, key, msg = self._classify(element_name)
            if classified_element:
                log.error('Selector failed, using test.ai classifier element')
                return classified_element
            else:
                raise Exception(msg)
        return None


    def find_element_by_tag_name(self, name, element_name=None):
        """
        Finds an element by tag name.

        :Args:
         - name - name of html tag (eg: h1, a, span)
         - element_name: The label name of the element to be classified.

        :Returns:
         - WebElement - the element if it was found

        :Raises:
         - NoSuchElementException - if the element wasn't found

        :Usage:
            ::

                element = driver.find_element_by_tag_name('h1')
        """
        if element_name is None:
            element_name = 'element_name_by_tag_name_%s' % (str(name).replace('.', '_'))
        element_name = element_name.replace(' ', '_')

        key = None
        msg = 'test.ai driver exception'

        # Run the standard selector
        try:
            driver_element = self.driver.find_element_by_tag_name(name)
            if driver_element:
                key = self._upload_screenshot_if_necessary(element_name)
                self._update_elem(driver_element, key, element_name)
            return driver_element
        except NoElementFoundException as e:
            log.exception(e)
        except Exception as err:
            # If this happens, then error during the driver call
            classified_element, key, msg = self._classify(element_name)
            if classified_element:
                log.error('Selector failed, using test.ai classifier element')
                return classified_element
            else:
                raise Exception(msg)
        return None


    def find_element_by_xpath(self, xpath, element_name=None):
        """
        Finds an element by xpath.

        :Args:
         - xpath - The xpath locator of the element to find.
         - element_name: The label name of the element to be classified.

        :Returns:
         - WebElement - the element if it was found

        :Raises:
         - NoSuchElementException - if the element wasn't found

        :Usage:
            ::

                element = driver.find_element_by_xpath('//div/td[1]')
        """
        if element_name is None:
            element_name = 'element_name_by_xpath_%s' % (str(xpath).replace('.', '_'))
        element_name = element_name.replace(' ', '_')

        key = None
        msg = 'test.ai driver exception'

        # Run the standard selector
        try:
            driver_element = self.driver.find_element_by_xpath(xpath)
            if driver_element:
                key = self._upload_screenshot_if_necessary(element_name)
                self._update_elem(driver_element, key, element_name)
            return driver_element
        except NoElementFoundException as e:
            log.exception(e)
        except Exception as err:
            # If this happens, then error during the driver call
            classified_element, key, msg = self._classify(element_name)
            if classified_element:
                log.error('Selector failed, using test.ai classifier element')
                return classified_element
            else:
                raise Exception(msg)
        return None

    def find_element_by_element_name(self, element_name):
        """
        Finds an element by test.ai element name.

        :Args:=
         - element_name: The label name of the element to be classified.

        :Returns:
         - WebElement - the element if it was found

        :Raises:
         - NoSuchElementException - if the element wasn't found
        """
        return self.find_by_element_name(element_name)

    def find_by_element_name(self, element_name):
        """
        Finds an element by element_name.

        :Args:
         - element_name: The label name of the element to be classified.

        :Returns:
         - WebElement - the element if it was found

        :Raises:
         - NoSuchElementException - if the element wasn't found

        :Usage:
            ::

                element = driver.find_by_element_name('some_label')
        """
        element_name = element_name.replace(' ', '_')
        el, key, msg = self._classify(element_name)

        if el is None:
            print(msg)
            raise Exception(msg)
        return el

    def _checkin(self):
        """
        Check in the current test.ai session.
        """
        data = {'api_key': self.api_key, 'os': platform.platform(), 'sdk_version': self.version, 'language': 'python3-' + sys.version, 'test_case_uuid': self.test_case_uuid}
        try:
            res = requests.post(self.url + '/sdk_checkin', json=data, timeout=1, verify=False)
        except Exception:
            pass

    def _get_screenshot(self):
        if self.use_cdp:
            screenshotBase64 = self.driver.execute_cdp_cmd('Page.captureScreenshot', {})['data']
        else:
            screenshotBase64 = self.driver.get_screenshot_as_base64()
        return screenshotBase64


    def _update_elem(self, elem, key, element_name, train_if_necessary=True):
        data = {
            'key': key,
            'api_key': self.api_key,
            'run_id': self.run_id,
            'label': element_name,
            'x': elem.rect['x'] * self.multiplier,
            'y': elem.rect['y'] * self.multiplier,
            'width': elem.rect['width'] * self.multiplier,
            'height': elem.rect['height'] * self.multiplier,
            'multiplier': self.multiplier,
            'train_if_necessary': train_if_necessary,
            'test_case_uuid': self.test_case_uuid
        }
        try:
            action_url = self.url + '/add_action'
            # Verify is False as the lets encrypt certificate raises issue on mac.
            _ = requests.post(action_url, json=data, verify=False)
        except Exception:
            pass

    def _classify(self, element_name):
        msg = ''
        if self.test_case_creation_mode:
            self._test_case_upload_screenshot(element_name)
            element_box = self._test_case_get_box(element_name)
            if element_box:
                if self.use_cdp:
                    parent_elem = None
                    real_elem = element_box
                else:
                    real_elem = self._match_bounding_box_to_selenium_element(element_box, multiplier=self.multiplier)
                    parent_elem = real_elem.parent
                element = testai_elem(parent_elem, real_elem, element_box, self.driver, self.multiplier)
                return element, self.last_test_case_screenshot_uuid, msg
            else:
                label_url = self.url + '/test_case/label/' + urllib.parse.quote(self.test_case_uuid)
                log.info('Waiting for bounding box of element {} to be drawn in the UI: \n\t{}'.format(element_name, label_url))
                webbrowser.open(label_url)
                while True:
                    element_box = self._test_case_get_box(element_name)
                    if element_box is not None:
                        print('Element was labeled, moving on')
                        if self.use_cdp:
                            parent_elem = None
                            real_elem = element_box
                        else:
                            real_elem = self._match_bounding_box_to_selenium_element(element_box, multiplier=self.multiplier)
                            parent_elem = real_elem.parent
                        element = testai_elem(parent_elem, real_elem, element_box, self.driver,
                                              self.multiplier)
                        return element, self.last_test_case_screenshot_uuid, msg
                    time.sleep(2)
        else:
            element = None
            run_key = None
            # Call service
            ## Get screenshot & page source
            screenshotBase64 = self._get_screenshot()
            key = self.get_screenshot_hash(screenshotBase64)
            resp_data = self._check_screenshot_exists(key, element_name)
            if resp_data['success'] and 'box' in resp_data:
                if self.debug:
                    print(f'Found cached box in action info for {element_name} using that')
                element_box = resp_data['box']
                if self.use_cdp:
                    parent_elem = None
                    real_elem = element_box
                else:
                    real_elem = self._match_bounding_box_to_selenium_element(element_box, multiplier=self.multiplier)
                    parent_elem = real_elem.parent
                element = testai_elem(parent_elem, real_elem, element_box, self.driver,
                                      self.multiplier)
                return element, key, msg
            source = ''

            # Check results
            try:
                data = {'screenshot': screenshotBase64, 'source': source,
                        'api_key':self.api_key, 'label': element_name, 'run_id': self.run_id}
                classify_url = self.url + '/classify'
                start = time.time()
                r = requests.post(classify_url, data=data, verify=False)
                end = time.time()
                if self.debug:
                    print(f'Classify time: {end - start}')
                response = json.loads(r.text)
                run_key = response['key']
                msg = response.get('message', '')
                if response.get('success', False):
                    log.info('successful classification of element_name: %s' % element_name)
                    element_box = response['elem']
                    if self.use_cdp:
                        parent_elem = None
                        real_elem = element_box
                    else:
                        real_elem = self._match_bounding_box_to_selenium_element(element_box, multiplier=self.multiplier)
                        parent_elem = real_elem.parent
                    element = testai_elem(parent_elem, real_elem, element_box, self.driver, self.multiplier)
                else:
                    if 'Please label' in msg or 'Did not find' in msg:
                        msg = 'Classification failed for element_name: %s - Please visit %s to classify' % (element_name, self.url + '/label/' + element_name + '?label=' + element_name)
                    elif 'frozen label' in msg:
                        msg = 'Classification failed for element_name: %s - However this element is frozen, so no new screenshot was uploaded. Please unfreeze the element if you want to add this screenshot to training' % element_name
                    if msg == '':
                        msg = 'Unknown error, here was the API response %s' % r.text
            except Exception:
                logging.exception('exception during classification')
            return element, run_key, msg

    def get_screenshot_hash(self, b64img):
        msg = base64.b64decode(b64img)
        buf = io.BytesIO(msg)
        img = Image.open(buf)
        w, h = img.size
        return hashlib.md5(img.crop((0, 75, w - 50, h - 75)).tobytes()).hexdigest()

    def _check_screenshot_exists(self, key, element_name):
        data = {'api_key': self.api_key, 'screenshot_uuid': key, 'label': element_name}
        check_screenshot_url = self.url + '/check_screenshot_exists'
        start = time.time()
        r = requests.post(check_screenshot_url, json=data, verify=False)
        end = time.time()
        if self.debug:
            print(f'Cached bounding box request time: {end - start}')

        if r.status_code != 200:
            raise Exception('Error checking cached screenshot from remote')
        else:
            response = json.loads(r.text)
            return response

    def _upload_screenshot_if_necessary(self, element_name):
        screenshotBase64 = self._get_screenshot()
        key = self.get_screenshot_hash(screenshotBase64)
        # Check results
        try:
            response = self._check_screenshot_exists(key, element_name)
            if self.debug:
                print(response)
            if response['success'] == True:
                if 'message' in response and response['message'] == 'frozen label':
                    if self.debug:
                        print(f'{element_name} is frozen, skipping upload')
                else:
                    if self.debug:
                        print(f'Screenshot {key} already exists on remote')
                return key
            else:
                if self.debug:
                    print(f'Screenshot {key} does not exist on remote, uploading it')
                data = {'api_key': self.api_key, 'screenshot_uuid': key, 'screenshot': screenshotBase64, 'label': element_name, 'test_case_uuid': self.test_case_uuid}
                upload_screenshot_url = self.url + '/upload_screenshot'
                start = time.time()
                r = requests.post(upload_screenshot_url, json=data, verify=False)
                end = time.time()
                if self.debug:
                    print(f'Upload screenshot request time: {end - start}')
                if r.status_code != 200:
                    log.error('Error uploading screenshot to remote')
                else:
                    pass
                return key
        except Exception:
            log.exception('Error checking cached screenshot / uploading it from remote')


    def _test_case_get_box(self, label):
        """
            Checks for a bounding box given the last screenshot uuid that we got when uploading it.
        """
        data = {'api_key': self.api_key, 'label': label, 'screenshot_uuid': self.last_test_case_screenshot_uuid, 'run_classifier': self.use_classifier_during_creation}
        if self.use_classifier_during_creation:
            data['screenshot'] = self.last_screenshot

        r = requests.post(self.url + '/test_case/get_bounding_box', json=data, verify=False)
        if r.status_code != 200:
            return None
        else:
            box = r.json()['box']
            return box

    def _test_case_upload_screenshot(self, label):
        """
            Uploads the screenshot to the server for test creation and retrieves the uuid / hash / key in return.
        """
        url = self.url + '/test_case/upload_screenshot'
        screenshotBase64 = self._get_screenshot()
        self.last_screenshot = screenshotBase64
        data = {'api_key': self.api_key, 'test_case_uuid': self.test_case_uuid, 'screenshot': screenshotBase64, 'label': label}
        r = requests.post(url, data=data, verify=False)
        if r.status_code == 200:
            res = r.json()
            if res['success']:
                self.last_test_case_screenshot_uuid = res['key']
                self.last_screenshot = screenshotBase64
            else:
                raise Exception('Failed to upload screenshot during test case creation')

    def update_test_case_status(self, test_case_name, status, message='', extra_info={}):
        url = self.url + '/test_case/set_test_case_status'
        data = {'api_key': self.api_key, 'test_case_status': status, 'message': message,
                'test_case_uuid': test_case_name, 'extra_info': extra_info}
        res = requests.post(url, json=data, verify=False)
        if res.status_code != 200:
            raise Exception('Failed to upload test case result')

    def _match_bounding_box_to_selenium_element(self, bounding_box, multiplier=1):
        """
            We have to ba hacky about this becasue Selenium does not let us click by coordinates.
            We retrieve all elements, compute the IOU between the bounding_box and all the elements and pick the best match.
        """
        # Adapt box to local coordinates
        new_box = {'x': bounding_box['x'] / multiplier, 'y': bounding_box['y'] / multiplier,
                   'width': bounding_box['width'] / multiplier, 'height': bounding_box['height'] / multiplier}
        # Get all elements
        elements = self.driver.find_elements_by_xpath("//*")
        # Compute IOU
        iou_scores = []
        for element in elements:
            try:
                iou_scores.append(self._iou_boxes(new_box, element.rect))
            except StaleElementReferenceException:
                iou_scores.append(0)
        composite = sorted(zip(iou_scores, elements), reverse=True, key=lambda x: x[0])
        # Pick the best match
        """
        We have to be smart about element selection here because of clicks being intercepted and what not, so we basically 
        examine the elements in order of decreasing score, where score > 0. As long as the center of the box is within the elements,
        they are a valid candidate. If none of them is of type input, we pick the one with maxIOU, otherwise we pick the input type,
        which is 90% of test cases.
        """
        composite = filter(lambda x: x[0] > 0, composite)
        composite = list(filter(lambda x: self._center_hit(new_box, x[1].rect), composite))

        if len(composite) == 0:
            raise NoElementFoundException('Could not find any web element under the center of the bounding box')
        else:
            for score, element in composite:
                if (element.tag_name == 'input' or element.tag_name == 'button') and score > composite[0][0] * 0.9:
                    return element
            return composite[0][1]

    def _iou_boxes(self, box1, box2):
        return self._iou(box1['x'], box1['y'], box1['width'], box1['height'], box2['x'], box2['y'], box2['width'], box2['height'])

    def _iou(self, x, y, w, h, xx, yy, ww, hh):
        return self._area_overlap(x, y, w, h, xx, yy, ww, hh) / (
                    self._area(w, h) + self._area(ww, hh) - self._area_overlap(x, y, w, h, xx, yy, ww, hh))

    def _area_overlap(self, x, y, w, h, xx, yy, ww, hh):
        dx = min(x + w, xx + ww) - max(x, xx)
        dy = min(y + h, yy + hh) - max(y, yy)
        if (dx >= 0) and (dy >= 0):
            return dx * dy
        else:
            return 0

    def _area(self, w, h):
        return w * h

    def _center_hit(self, box1, box2):
        box1_center = box1['x'] + box1['width'] / 2, box1['y'] + box1['height'] / 2
        if box1_center[0] > box2['x'] and box1_center[0] < box2['x'] + box2['width'] and box1_center[1] > box2['y'] and box1_center[1] < box2['y'] + box2['height']:
            return True
        else:
            return False

class testai_elem(webdriver.remote.webelement.WebElement):
    def __init__(self, parent, source_elem, elem, driver, multiplier=1.0):
        self._is_real_elem = False
        if not isinstance(source_elem, dict):
            # We need to also pass the _w3c flag otherwise the get_attribute for thing like html or text is messed up
            if old_selenium:
                super(testai_elem, self).__init__(source_elem.parent, source_elem._id, w3c=source_elem._w3c)
            else:
                super(testai_elem, self).__init__(source_elem.parent, source_elem._id)
            self._is_real_elem = True
        self.driver = driver
        self.multiplier = multiplier
        self._text = elem.get('text', '')
        self._size = {'width': elem.get('width', 0)/multiplier, 'height': elem.get('height', 0)/multiplier}
        self._location = {'x': elem.get('x', 0)/multiplier, 'y': elem.get('y', 0)/multiplier}
        self._property = elem.get('class', '')
        self._rect = {}
        self.rect.update(self._size)
        self.rect.update(self._location)
        self._tag_name = elem.get('class', '')
        self._cx = elem.get('x', 0)/multiplier + elem.get('width', 0) / multiplier / 2
        self._cy = elem.get('y', 0)/multiplier + elem.get('height', 0) /multiplier / 2

    @property
    def size(self):
        return self._size
    @property
    def location(self):
        return self._location
    @property
    def rect(self):
        return self._rect
    @property
    def tag_name(self):
        return self._tag_name

    def click(self, js_click=False):
        if self._is_real_elem == True:
            if not js_click:
                webdriver.remote.webelement.WebElement.click(self)
            else:
                # Multiplier needs to be undone as js doesn't care about it. only selenium/appium
                self.driver.execute_script('document.elementFromPoint(%d, %d).click();' % (int(self._cx), int(self._cy)))
        else:
            # Multiplier needs to be undone as js doesn't care about it. only selenium/appium
            self.driver.execute_cdp_cmd('Input.dispatchMouseEvent', { 'type': 'mousePressed', 'button': 'left', 'clickCount': 1, 'x': self._cx, 'y': self._cy})
            time.sleep(0.05)
            self.driver.execute_cdp_cmd('Input.dispatchMouseEvent', { 'type': 'mouseReleased', 'button': 'left', 'clickCount': 1, 'x': self._cx, 'y': self._cy})

    def send_keys(self, value, click_first=True):
        if click_first:
            self.click()
        actions = ActionChains(self.driver)
        actions.send_keys(value)
        actions.perform()

    def submit(self):
        self.send_keys('\n', click_first=False)

class NoElementFoundException(Exception):
    pass