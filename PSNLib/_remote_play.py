import Vis
import time
import difflib
import subprocess
from PSNLib._utils import relativeItem
from PSNLib._psOCR import recogniseGame, PsOCRException
from utils3.system import allProcesses, command

# Static Values
REMOTE_PLAY_APPLICATION = '/Applications/RemotePlay.app'
NOT_SIGNED_IN = 'Sign In to PSNLib'
SIGNED_IN = 'Select the last console you connected to'
SEARCHING_FOR_CONNECTIONS = 'Searching for connections nearby...'
CONNECTING_PS5 = 'Connecting and turning on your PS5...'
CHECKING_NETWORK = 'Checking the network..'
CHECKING_NETWORK2 = 'Checking the network.'
CHECKING_NETWORK3 = 'Checking the network...'
CONNECTED = 'connected using Remote'


def _noGarbageFiles(func):
    def wrapper(*args, **kwargs):
        for a in args:
            if (a == '.DS_Store') or (a.endswith('.DS_Store') == True):
                raise AssertionError('Garbage file passed:', a)

            return func(*args, **kwargs)


class RemotePlayError(Exception):
    pass


class _MouseClick:
    def __init__(self, executable_pt=None):
        self._executable_pt = executable_pt

    def click(self, x, y):
        assert self._executable_pt is not None, 'Executable path is not set.'
        subprocess.check_call([self._executable_pt, 'c:{},{}'.format(x, y)])

    def pressDownClick(self, x, y, press_duration):
        assert self._executable_pt is not None, 'Executable path is not set.'
        subprocess.check_call([
            self._executable_pt, 'dd:{},{}'.format(x, y),
        ])
        time.sleep(press_duration)
        subprocess.check_call([
            self._executable_pt, 'du:{},{}'.format(x, y),
        ])


class _OsaScriptHelper(_MouseClick):
    def __init__(self, cliclick_pt=None):
        super().__init__(cliclick_pt)

    @staticmethod
    def execute(script):
        """Executes a script."""
        return command(['osascript', '-e', script], read=True, wait=True)

    @staticmethod
    def foreground():
        foreground = command(['osascript', '-e', 'tell application "System Events" to name of first '
                                                 'application process whose frontmost is true'],
                             read=True)

        return foreground.split('\n')[0]

    def darkMode(self):
        """Change the system to dark mode."""
        script = """
        tell application "System Events"
            tell appearance preferences
                set dark mode to true
            end tell
        end tell
        """
        self.execute(script)

    def lightMode(self):
        """Change the system to light mode."""
        script = """
        tell application "System Events"
            tell appearance preferences
                set dark mode to false
            end tell
        end tell
        """
        self.execute(script)

    def isDarkMode(self):
        """Get the current appearance mode."""
        script = """
        tell application "System Events"
            tell appearance preferences
                return dark mode
            end tell
        end tell
        """
        output = self.execute(script)[0].replace('\n', '').strip()
        if output.startswith('t'):
            return True
        elif output.startswith('f'):
            return False
        else:
            raise ValueError("Could not get dark mode status")

    def setFullScreen(self):
        """Set the application to full screen."""
        script = """
        tell application "System Events"
            key code 3 using {command down, control down}
        end tell
        """
        self.execute(script)

    def rightArrow(self):
        """Press the right arrow key."""
        self._pressKeyCode(124)

    def leftArrow(self):
        """Press the left arrow key."""
        self._pressKeyCode(123)

    def _pressKeyCode(self, code):
        script = """
        tell application "RemotePlay" to activate
        delay 1
        tell application "System Events"
            set c to {}
            key down c
            delay 0.1
            key up c
        end tell
        """.format(code)
        self.execute(script)

    def escapeKey(self):
        self._pressKeyCode(53)

    def enterKey(self):
        self._pressKeyCode(36)

    def deleteKey(self):
        self._pressKeyCode(51)


class _SaveColor(_OsaScriptHelper):
    def __init__(self):
        super().__init__()
        self._dark = False

    def __enter__(self):
        self._dark = self.isDarkMode()
        if not self._dark:
            self.darkMode()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._dark:
            self.darkMode()
        else:
            self.lightMode()


# Run a function in dark mode
def inDarkMode(func):
    def inDarkWrapper(*args, **kwargs):
        with _SaveColor():
            return func(*args, **kwargs)

    return inDarkWrapper


class _RemotePlayBasic(_OsaScriptHelper):
    def __init__(self, clicker):
        super().__init__(cliclick_pt=clicker)

    def open(self):
        if not self.foreground() == 'RemotePlay':
            subprocess.check_call(['open', REMOTE_PLAY_APPLICATION])

        max_time = 10
        while not self.foreground() == 'RemotePlay':
            time.sleep(0.1)
            max_time -= 0.1
            if max_time <= 0:
                raise RemotePlayError("Could not open RemotePlay app")

        time.sleep(1)

    def close(self):
        if self.isRunning():
            subprocess.check_call(['killall', 'RemotePlay'])

    @staticmethod
    def isRunning():
        for proc in allProcesses():
            if proc.cmd.__contains__(REMOTE_PLAY_APPLICATION):
                return True
        return False


class RemotePlay(_RemotePlayBasic):
    def __init__(self, cliclick, logger=print):
        super().__init__(cliclick)
        self._ocr = Vis.OCR()
        self._logger = logger

    @inDarkMode
    def connect(self):
        # Compare what's on the screen now and what will be on the screen after we open the RemotePlay
        # app this way we just get the new and relevant text.
        with Vis.ScreenShot() as ss_old:
            old_text = self._ocr.recognize(ss_old)
            self.open()  # Open the RemotePlay app
            with Vis.ScreenShot() as ss:
                text = self._ocr.recognize(ss)
                for z in old_text:
                    if z in text:
                        text.remove(z)

        if NOT_SIGNED_IN in text:
            raise RemotePlayError("Not signed in to PSNLib, Please login and try again...")
        assert SIGNED_IN in text, "Could not find the connect button"

        # Every one has a different PSNLib name, so we are going to find a static element and transform
        # the coordinates to the connect button via a static offset.
        x, y = Vis.ImageCords(relativeItem('other connections.png')).cords
        # Static offset...
        y -= 50
        x += 20
        self._log('Connecting to PSNLib...')
        self.click(x, y)
        time.sleep(2)
        self._log('Muting the system while we wait for the PS5 to connect...')

        connected = False

        buffer = 100

        while not connected:
            time.sleep(0.1)
            with Vis.ScreenShot() as ss:
                text = self._ocr.recognize(ss)
                for z in text:
                    if z.__contains__(CONNECTED):
                        self._log('Connected to PS5!')
                        connected = True
                        break

                if (CHECKING_NETWORK in text) or (CHECKING_NETWORK2 in text) \
                        or (CHECKING_NETWORK3 in text):
                    self._log('Checking the network...')
                elif CONNECTING_PS5 in text:
                    self._log('Connecting to PS5...')
                elif SEARCHING_FOR_CONNECTIONS in text:
                    self._log('Searching for connections...')
                else:
                    buffer -= 1

    def _log(self, msg):
        self._logger(msg)

    @staticmethod
    def _extractGameName(image: str) -> str:

        # Depreciated due to new Swift PSNLib Detection System
        # New system uses CoreImage to preform cropping and OCR on the provided image to extract
        # the game name.

        # ----------
        # """Check if the game name"""
        # img = cv2.imread(image)
        # assert img is not None, 'Unable to load image'
        # # Split the image in half horizontally
        # height, width, _ = img.shape
        # # cut the height in 1/2
        # cut_off_h = int(height / 2)
        # # Cuts the image to only the line with the game name on it
        # game_name_img = ((img[:cut_off_h, :])[530:, :])[:80, :]
        # with Container() as c:
        #     pt = c.join('game.png', modify=False).path
        #     cv2.imwrite(pt, game_name_img)
        #     text: list = self._ocr.recognize(pt)
        #     if len(text) > 1:
        #         if 'arg' in text:
        #             text = [text[text.index('arg') + 1]]
        #     else:
        #         text[0] = text[0][3:].strip()
        #
        #     return text[0].lower()
        # ----------

        return recogniseGame(image).lower()

    def openGame(self, gameName):
        gameName = gameName.lower()
        assert isinstance(gameName, str)
        self.open()
        self.setFullScreen()
        time.sleep(1)


        # Click the ps button to make sure we are in the view of all  the games
        button_img = relativeItem('ps button.png')
        x, y = Vis.ImageCords(button_img).cords
        self.pressDownClick(x, y, 3)

        def _goToLibrary():
            self.deleteKey()
            self.escapeKey()


        # check if the item on the screen now is the playstation store
        for _ in range(10):
            try:
                _goToLibrary()  # This new system is much faster as it checks if the store is on screen rather than
                # waiting a fixed amount of time
                time.sleep(0.5)
                with Vis.ScreenShot() as ss:
                    item_name = self._extractGameName(ss)
                    assert difflib.SequenceMatcher(None, item_name,
                                                   'playstation store').ratio() > 0.8, 'Unable to find ' \
                                                                                       'the playstation store'

                    break
            except AssertionError:
                time.sleep(1)


        for _ in range(100):
            self.rightArrow()
            time.sleep(0.2)

            with Vis.ScreenShot() as ss:
                try:
                    item_name = self._extractGameName(ss)
                except PsOCRException:
                    with Vis.ScreenShot() as s2:
                        item_name = self._extractGameName(s2)


                # self._log('Current Item on screen: {}'.format(item_name))
                r = difflib.SequenceMatcher(None, item_name, gameName).ratio()

                if item_name.__contains__(':'):
                    # self._log('Game name contains a colon, checking for a match without the colon...')
                    r2 = difflib.SequenceMatcher(None, item_name.split(':')[0], gameName).ratio()
                    # self._log('GameName:{} ItemName:{} r2{}'.format(gameName, item_name, r2))
                    if r2 > r:
                        r = r2
                else:
                    # self._log('GameName{} ItemName{} r{}'.format(gameName, item_name, r))
                    pass
                # self._log('Current Ratio: {}'.format(r.__round__(2)))
                if r > 0.8:
                    self._log('Found game: {}'.format(gameName))
                    self._log('Opening game...')
                    self.enterKey()
                    return
                elif (difflib.SequenceMatcher(None, item_name, 'Game Library').ratio() > 0.8) or (
                        difflib.SequenceMatcher(None, item_name, 'Library').ratio() > 0.8):
                    raise RemotePlayError('Unable to find game: {}'.format(gameName))

        raise RemotePlayError('Attempted to find game: {} 100 times, unable to find it'.format(gameName))


if __name__ == '__main__':
    def speaker(words):
        print(words)
        subprocess.check_call(['say', words])

    # noinspection SpellCheckingInspection
    rp = RemotePlay('/Users/Sal/Projects/CrossLanguage/Dart/Builds/Dart2.1/Assets/cliclick', logger=speaker)
    rp.connect()
    rp.openGame('call of duty')
