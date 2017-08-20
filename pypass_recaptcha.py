import pydub
import speech_recognition
import time
import urllib
import signal
from selenium.common.exceptions import NoSuchElementException

rec = speech_recognition.Recognizer()


def sig_handler(signum, frame):
    """
    A handler for making sure the speech recognition doesn't hang.
    
    :param signum: signal.SIGALRM
    :param frame: signal handler
    :return: 
    """
    print 'Function timeout.'
    raise Exception('Function timed out.')


def pypass_recaptcha(browser, link, num_tries=10, sleep_time=0.5, timeout=30):
    """
    Meant to be used with selenium, this function keeps trying to download and solve ReCaptcha challenges using speech 
    recognition.
    
    :param browser: the selenium browser
    :param link: url to the page with the ReCaptcha
    :param num_tries: number of tries to try everything again
    :param sleep_time: time (seconds) to act as a buffer between attempts
    :param timeout: time (seconds) to wait for speech recognition to complete an attempt
    :return: \0 on failure, void otherwise
    """
    for i in range(num_tries):
        # Download recaptcha mp3 file
        for j in range(num_tries):
            # Go to url
            for k in range(num_tries):
                try:
                    browser.get(link)
                    break
                except Exception:
                    print 'Could not get link, try %d' % k
                    time.sleep(sleep_time)
            # Keep trying to download the audio challenge mp3 file
            for k in range(num_tries):
                try:
                    # TODO: Find the correct xpath to the "Get an audio challenge" button
                    ac_button_xpath = '/html/body/table/tbody/tr[3]/td/form/table/tbody/tr[1]/td/table/tbody/tr/td[2]/div/div/table/tbody/tr[1]/td[2]/a[2]'
                    audio_challenge_button = browser.find_element_by_xpath(ac_button_xpath)
                    if audio_challenge_button.get_attribute('title') == 'Get an audio challenge':
                        browser.find_element_by_xpath(ac_button_xpath + 'img').click()
                    # TODO: Find the correct xpath to the "Download mp3" button
                    mp3_button_xpath = '/html/body/table/tbody/tr[3]/td/form/table/tbody/tr[1]/td/table/tbody/tr/td[2]/div/div/table/tbody//tr[1]/td[1]/center/div/span[1]/a'
                    mp3_link = browser.find_element_by_xpath(mp3_button_xpath).get_attribute('href')
                    urllib.urlretrieve(mp3_link, 'tmp/recaptcha.mp3')  # Download the mp3
                    break
                except NoSuchElementException:
                    print 'No challenge button found, try %d' % k
            # Try to convert the .mp3 to .wav for sr; ffmpeg also works
            try:
                recaptcha_mp3 = pydub.AudioSegment.from_mp3('tmp/recaptcha.mp3')
                recaptcha_mp3.export('tmp/recaptcha.wav', format='wav')
            except Exception:
                print 'Mp3 error, reloading url...'
                continue  # Restart the whole process on exception
            # Register a timeout
            signal.signal(signal.SIGALRM, sig_handler)
            signal.alarm(timeout)
            # Try to recognize the .wav
            print 'Recognition attempt: %d' % (j + 1)
            try:
                with speech_recognition.AudioFile('tmp/recaptcha.wav') as source:
                    audio = rec.record(source)
            except Exception:
                'Fatal recognition failure, reloading url...'
                continue  # Restart the whole process on exception
            finally:
                signal.alarm(0)  # Reset the alarm on a successful recognition
            # Google speech recognition tends to group numbers into phone numbers; this is actually what makes this work so well
            recaptcha_value = rec.recognize_google(audio).replace('-', '')
            # If all numbers, try to submit
            if recaptcha_value.isdigit():
                print 'Recognition success!'
                browser.find_element_by_id('recaptcha_response_field').send_keys(recaptcha_value)
                # TODO: Find the correct xpath to the submit button
                submit_button_xpath = '/html/body/table/tbody/tr[3]/td/form/table/tbody/tr[2]/td/a[1]/img'
                browser.find_element_by_xpath(submit_button_xpath).click()  # Click the submit button
                # If this attempt was successful, do something
                if 'Please enter correct' not in str(browser.page_source.encode('utf-8')):
                    pass  # TODO: Replace this line with whatever you want to do after pypassing the ReCaptcha
                # Otherwise, try again
                else:
                    print 'Recaptcha failure, trying again...'
            else:
                print 'Recognition failure, trying again...'
    # return "\0" on failure
    return '\0'