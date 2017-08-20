import pydub
import speech_recognition
import time
import urllib
import signal
from selenium.common.exceptions import NoSuchElementException

rec = speech_recognition.Recognizer()


def sig_handler(signum, frame):
    """
    A handler for making sure speech recognition doesn't hang.
    
    :param signum: signal.SIGALRM
    :param frame: signal handler
    :return: None
    """
    print('Function timeout.')
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
    # Overall try loop
    for i in range(num_tries):
        # Try loop to go to the url with the ReCaptcha challenge
        for j in range(num_tries):
            try:
                browser.get(link)  # Have the selenium browser go to the link
                break  # Break loop on success
            except Exception:  # If some exception was thrown (most likely some page elements weren't fully loaded)
                print('Could not get link, attempt %d' % j)  # Print an error message
                time.sleep(sleep_time)  # Wait a while before trying again
        # Try loop to download the audio challenge .mp3 file
        for j in range(num_tries):
            try:
                # TODO: Find the correct xpath to the "Get an audio challenge" button
                ac_button_xpath = '/html/body/table/tbody/tr[3]/td/form/table/tbody/tr[1]/td/table/tbody/tr/td[2]/div/div/table/tbody/tr[1]/td[2]/a[2]'
                audio_challenge_button = browser.find_element_by_xpath(ac_button_xpath)  # Get the button element
                if audio_challenge_button.get_attribute('title') == 'Get an audio challenge':  # If the title class of the button element is correct
                    browser.find_element_by_xpath(ac_button_xpath + 'img').click()  # Click the button
                # TODO: Find the correct xpath to the "Download mp3" button
                mp3_button_xpath = '/html/body/table/tbody/tr[3]/td/form/table/tbody/tr[1]/td/table/tbody/tr/td[2]/div/div/table/tbody//tr[1]/td[1]/center/div/span[1]/a'
                mp3_link = browser.find_element_by_xpath(mp3_button_xpath).get_attribute('href')  # Get the link to download the audio challenge .mp3 file
                urllib.urlretrieve(mp3_link, 'pypass-recaptcha.mp3')  # Download the .mp3 file
                break  # Break loop on success
            except NoSuchElementException:  # If no audio challenge button or download mp3 button (most likely incorrect xpath)
                print('No challenge button found, attempt %d' % j)  # Print an error message
        try:  # Try to convert the .mp3 file to a .wav file for speech recognition
            recaptcha_mp3 = pydub.AudioSegment.from_mp3('pypass-recaptcha.mp3')  # Create an AudioSegment from the .mp3 file
            recaptcha_mp3.export('pypass-recaptcha.wav', format='wav')  # Export the AudioSegment as a .wav file
        except Exception:  # If an exception was thrown during conversion
            print('Mp3 error, reloading url...')  # Print an error message
            continue  # Restart the whole process
        signal.signal(signal.SIGALRM, sig_handler)  # Register a timeout
        signal.alarm(timeout)  # Set the timeout time
        print('Recognition attempt: %d' % (i + 1))  # Print a message to keep track of recognition attempts
        try:  # Try to recognize the .wav
            with speech_recognition.AudioFile('pypass-recaptcha.wav') as source:  # Using the .wav file as a source
                audio = rec.record(source)  # Try to recognize the .wav file
        except Exception:  # If an exception was thrown (most likely a timeout)
            print('Fatal recognition failure, reloading url...')  # Print an error message
            continue  # Restart the whole process
        finally:  # If the speech recognition was a success
            signal.alarm(0)  # Reset the alarm
        recaptcha_value = rec.recognize_google(audio).replace('-', '')  # Google speech recognition tends to group numbers into phone numbers; this is actually what makes this work so well
        if recaptcha_value.isdigit():  # If all characters in the recognition attempt are digits
            print('Recognition success!')  # Celebrate with a message
            browser.find_element_by_id('recaptcha_response_field').send_keys(recaptcha_value)  # Send the recognition string to the ReCaptcha response field
            # TODO: Find the correct xpath to the submit button
            submit_button_xpath = '/html/body/table/tbody/tr[3]/td/form/table/tbody/tr[2]/td/a[1]/img'
            browser.find_element_by_xpath(submit_button_xpath).click()  # Click the submit button
            incorrect_recaptcha_string = 'Please enter correct'  # String that appears ONLY when an incorrect ReCaptcha is entered
            if incorrect_recaptcha_string in str(browser.page_source.encode('utf-8')):  # If the string is present
                print('Recaptcha failure, trying again...')  # Print an error message
                continue  # Restart the whole process
            else: # If the string isn't there, then success!
                pass  # TODO: Replace this line with whatever you want to do after pypassing the ReCaptcha
                return 0  # Return 0 on success
        else:  # If not all of the characters in the recognition attempt are digits
            print('Recognition failure, trying again...')  # Print an error message
            continue  # Restart the whole process
    return -1  # Return -1 on failure