# -*- coding: utf-8 -*-
#
####################################################
#
# PRISM - Pipeline for animation and VFX projects
#
# www.prism-pipeline.com
#
# contact: contact@prism-pipeline.com
#
####################################################
#
#
# Copyright (C) 2016-2018 Richard Frangenberg
#
# Licensed under GNU GPL-3.0-or-later
#
# This file is part of Prism.
#
# Prism is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Prism.  If not, see <https://www.gnu.org/licenses/>.


import os, sys, traceback, io, time, subprocess, platform
from functools import wraps
import trelloprism, trelloqt
try:
    import snapdraw
except ImportError:
    snapdraw = None
try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except ImportError:
    from PySide.QtCore import *
    from PySide.QtGui import *

if sys.version[0] == "3":
    pVersion = 3
else:
    pVersion = 2

from PrismUtils.Decorators import err_catcher_plugin as err_catcher

"""
Prism-facing side of Trello-Prism integration.
This is the plugin object registered with Prism.
Its methods run on various user actions within Prism.
Connect to Trello using trelloprism module with its handler class.
"""

# TODO: ADD "VIEW ON TRELLO" TO RIGHT CLICK MENUS


class Prism_PrismTrello_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin
        self.trello_handler = None


    # if returns true, the plugin will be loaded by Prism
    @err_catcher(name=__name__)
    def isActive(self):
        return True


    def is_enabled(self):
        """
        :return: (bool) whether or not this feature is enabled for the project
        """
        # return eval(self.core.getConfig("trello", "enabled", configPath=self.core.prismIni) or "False")
        check = self.core.getConfig("trello", "enabled", configPath=self.core.prismIni)
        print("TRELLO INTEGRATION : {}. - Change it on Prism Project Settings.".format(check))
        return check


    @err_catcher(name=__name__)
    def reload_handler(self):
        """
        Refresh the handler object and ensure connection.
        :return:
        """
        self.trello_handler = trelloprism.TrelloHandler(self.core)
        if not self.trello_handler.is_connected:
            QMessageBox(text="Trello connection rejected.\nCheck internet connection or Trello credentials.").exec_()


    @err_catcher(name=__name__)
    def sync_down(self):
        """
        Dummy slot because UI can't be connected directly to handler.
        This class is the interface.
        :return: None
        """
        if not self.is_enabled():
            return

        self.reload_handler()
        win = QProgressDialog("Downloading changes from Trello...", "Cancel", 0, 1)
        win.show()
        def inc(): win.setValue(win.value() + 1)
        self.trello_handler.sync_from_trello(set_max_func=win.setMaximum, increment_func=inc)
        win.accept()
        QMessageBox(text="Sync complete.").exec_()


    @err_catcher(name=__name__)
    def sync_up(self):
        """
        Slot to pass sync up call to handler.
        :return: None
        """
        if not self.is_enabled():
            return

        self.reload_handler()
        win = QProgressDialog("Uploading changes to Trello...", "Cancel", 0, 1)
        win.show()
        def inc(): win.setValue(win.value() + 1)
        self.trello_handler.sync_from_prism(set_max_func=win.setMaximum, increment_func=inc)
        win.accept()
        QMessageBox(text="Sync complete.").exec_()

    # the following function are called by Prism at specific events, which are indicated by the function names
    # you can add your own code to any of these functions.

    @err_catcher(name=__name__)
    def onProjectChanged(self, origin):
        # runs when opened for first time - this is ideal place to connect to Trello
        # and gdrive project structure - or maybe make a button in settings which does it?
        # "Sync tasks with Trello"
        # origin == core
        # this is the soonest it can connect to Trello,
        # because project settings are needed.
        if not self.is_enabled():
            return

        self.reload_handler()


    @err_catcher(name=__name__)
    def onProjectBrowserStartup(self, origin):
        pass


    @err_catcher(name=__name__)
    def onProjectBrowserClose(self, origin):
        pass


    @err_catcher(name=__name__)
    def onPrismSettingsOpen(self, origin):
        """
        Add a groupbox for Trello integration to the project page of settings
        :param origin: the settings ui object
        :return: None
        """
        page = origin.w_prjSettings
        trello_widg = trelloqt.TrelloSettingsUi(self.core, page)
        page.layout().insertWidget(6, trello_widg)
        trello_widg.sync_down_button.clicked.connect(self.sync_down)
        trello_widg.sync_up_button.clicked.connect(self.sync_up)


    @err_catcher(name=__name__)
    def onPrismSettingsSave(self, origin):
        pass


    @err_catcher(name=__name__)
    def onStateManagerOpen(self, origin):
        pass


    @err_catcher(name=__name__)
    def onStateManagerClose(self, origin):
        pass


    @err_catcher(name=__name__)
    def onSelectTaskOpen(self, origin):
        pass


    # @err_catcher(name=__name__)
    # def onStateCreated(self, origin):
    #     pass


    @err_catcher(name=__name__)
    def onStateDeleted(self, origin):
        pass


    @err_catcher(name=__name__)
    def onPublish(self, origin):
        """
        Only happens ONCE per publish
        and doesn't contain info about the individual states.
        """
        # print("PUBLIIIIIIIIIISH")
        self.reload_handler()


    @err_catcher(name=__name__)
    def onSaveFile(self, origin, filepath):
        pass


    @err_catcher(name=__name__)
    def onAssetDlgOpen(self, origin, assetDialog):
        pass


    @err_catcher(name=__name__)
    def onAssetCreated(self, origin, assetName, assetPath, assetDialog=None):
        pass


    @err_catcher(name=__name__)
    def onShotCreated(self, origin, sequenceName, shotName):
        pass


    @err_catcher(name=__name__)
    def preLoadEmptyScene(self, origin, *args):
        pass


    @err_catcher(name=__name__)
    def postLoadEmptyScene(self, origin, *args):
        pass


    @err_catcher(name=__name__)
    def preImport(self, *args, **kwargs):
        pass


    @err_catcher(name=__name__)
    def postImport(self, *args, **kwargs):
        """
        Check if the imported asset needs REVIEW (art or tech). If so, opens the REVIEW popup.
        User can take screenshots, make annotations & comments, (pipe dream: video),
        and switch between "approve for {next step}" or "request {prev step} changes".
        All of this is then posted to the card on Trello (along with version, ofc).
        """
        pass


    @err_catcher(name=__name__)
    def preExport(self, *args, **kwargs):
        pass


    @err_catcher(name=__name__)
    def postExport(self, *args, **kwargs):
        # empty args, only kwargs
        self.publish_task_to_trello("Export", kwargs)


    @err_catcher(name=__name__)
    def prePlayblast(self, *args, **kwargs):
        pass


    @err_catcher(name=__name__)
    def postPlayblast(self, *args, **kwargs):
        # empty args, only kwargs
        self.publish_task_to_trello("Playblast", kwargs)


    @err_catcher(name=__name__)
    def preRender(self, *args, **kwargs):
        pass


    @err_catcher(name=__name__)
    def postRender(self, *args, **kwargs):
        # empty args, only kwargs
        self.publish_task_to_trello("Render", kwargs)


    @err_catcher(name=__name__)
    def publish_task_to_trello(self, task_type, task_data):
        """
        Respond to a publish and propogate the necessary change to Trello.
        onPublish refreshes handler object, since that only runs once per publish set.
        :param task_type: Export, Playblast, or ImageRender
        :param task_data: kwargs given to the callback function
        :return: None
        """
        if not self.is_enabled() or not self.trello_handler or not self.trello_handler.is_connected:
            return

        print("*************************************************************")
        scene_file = os.path.normpath(task_data["scenefile"])
        publish_file = os.path.normpath(task_data["outputpath"])
        localEnabled = self.core.getConfig(
            "globals", "uselocalfiles", configPath=self.core.prismIni)
        if localEnabled and publish_file.startswith(os.path.normpath(self.core.localProjectPath)):
            # "Local Output", no Trello action to be taken
            print("{}\nTHE PUBLISH IS MARKED AS LOCAL ONLY. NOT POSTED TO TRELLO.".format(publish_file))
            return

        data = self.get_publish_data(scene_file, publish_file, task_type)
        data["start_frame"], data["end_frame"] = task_data["startframe"], task_data["endframe"]
        data["attach"], data["attach_type"] = self.get_publish_attachment(data)
        try:
            self.trello_handler.publish_to_card(data)
        except:
            raise

        # db = discordbot.DiscordHandler(self.core)
        # db.post_publish_embed(data)


    def get_publish_data(self, scene_file, publish_file, task_type):
        """
        Read export data needed for Trello from file names.
        :param scene_file: path to export's source file
        :param publish_file: path to exported file
        :param task_type: the type of publish, passed by thing I guess?
        :return:
        """
        scene_dirs = scene_file.split(os.sep)
        publish_split = publish_file.split(os.sep)
        # project_steps = eval(self.core.getConfig(
        #     "globals", "pipeline_steps", configPath=self.core.prismIni))
        project_steps = self.core.getConfig(
            "globals", "pipeline_steps", configPath=self.core.prismIni)

        data = {"author": self.core.username,
                "plugin": self.core.appPlugin.pluginName,
                "publish_file": publish_file}
        # export path is completely different based on export/playblast/render
        # LOLOLOLOLOLOLOLOLOL
        if task_type == "Export":
            # base_path = os.path.join(*publish_split[:-5])
            base_path = os.path.sep.join(publish_split[:-5])
            data["entity"] = publish_split[-6]
            data["task"] = publish_split[-4]
            vinfo_path = os.path.normpath(os.path.join(publish_file, "..", "..", "versioninfo.yml"))
        elif task_type == "Playblast":
            # base_path = os.path.join(*publish_split[:-4])
            base_path = os.path.sep.join(publish_split[:-4])
            data["entity"] = publish_split[-5]
            data["task"] = publish_split[-3]
            vinfo_path = os.path.normpath(os.path.join(publish_file, "..", "versioninfo.yml"))
        elif task_type == "Render":
            # base_path = os.path.join(*publish_split[:-6])
            base_path = os.path.sep.join(publish_split[:-6])
            data["entity"] = publish_split[-7]
            data["task"] = publish_split[-4]
            vinfo_path = os.path.normpath(os.path.join(publish_file, "..", "..", "versioninfo.yml"))
            # correct task_type - make more specific
            task_type = next(t for t, subpath in self.trello_handler.task_paths.items()
                             if subpath in publish_file)
        else:
            raise ValueError("Unknown publish type.")

        # print("SCENE PATH: {}".format(scene_file))
        # print("PUBLISH PATH: {}".format(publish_file))
        # print("BASE PATH: {}".format(base_path))

        data["type"] = task_type
        # data["category"] = os.path.basename(os.path.dirname(base_path))
        data["comment"] = os.path.basename(os.path.dirname(vinfo_path)).split("_")[1]
        entity = os.path.basename(base_path)
        ap = os.path.normpath(self.core.getAssetPath())
        sp = os.path.normpath(self.core.getShotPath())

        if publish_file.startswith(ap):
            # Asset
            data["pipe"] = "assets"
            data["step"] = project_steps[scene_dirs[-3]]
            data["entity"] = entity
            # data["category"] = os.path.basename(os.path.dirname(base_path))
            data["category"] = os.path.relpath(os.path.dirname(base_path), ap).replace(os.path.sep, "/")
        elif publish_file.startswith(sp):
            # Shot
            data["pipe"] = "shots"
            data["step"] = project_steps[scene_dirs[-3]]
            data["category"], data["entity"] = entity.split("-", 1)
        else:
            raise EnvironmentError("Can't find file in pipeline!")

        # get some stuff from version .ini
        task_subpath = self.trello_handler.task_paths[data["type"]]
        data["task_path"] = os.path.join(base_path, task_subpath, data["task"])
        # config_items = dict(self.core.getConfig(configPath=vinfo_path, getItems=True, cat="information"))
        config_items = dict(self.core.getConfig(configPath=vinfo_path, cat="information"))

        data["version"] = config_items["Version"]
        data["timestamp"] = config_items["Creation date"]
        # data["dependencies"] = eval(config_items["dependencies"])
        if "Dependencies" in config_items:
            data["dependencies"] = config_items["Dependencies"]

        return data


    def get_publish_attachment(self, data):
        """
        Get an attachment for the publish in requests-ready form
        :param data:
        :return: bytesIO object (readable)
        """
        # ffmpeg -framerate 24 -apply_trc iec61966_2_1 -i input.mp4 -c:v libvpx-vp9 -b:v 2M -fs 8000000 -pass 2 -y output.webm
        # FIRST take care of VIDEO possibilities
        pub = data["publish_file"]
        # print(os.path.splitext(pub)[-1])
        # mp4 = pub.replace("..jpg", ".mp4")
        mp4 = os.path.splitext(pub)[0].rstrip(os.extsep) + ".mp4"
        if os.path.exists(mp4):
            # still convert for consistency and file size
            return self.get_video_buffer(mp4), "webm"
        # if os.path.splitext(pub)[-1] in (".mp4", ".mov", ".avi", ".webm"):
        #     return self.get_video_buffer(pub), "webm"

        # now guaranteed to be frame inputs
        sf = "{:04d}".format(data["start_frame"])
        frame_input = ""
        if data["type"] == "Playblast":
            # get ffmpeg args - input file should be blahblah.{:04d}.ext
            # but leave start_frame for -start_number ffmpeg arg
            frame_input = pub.replace("..", ".%04d.")
            return self.get_video_buffer(frame_input), "webm"
        elif data["type"] == "Render":
            # current pub file is blahblah.exr
            for f in os.listdir(os.path.dirname(pub)):
                if ".{}.".format(sf) in f:
                    ext = os.path.splitext(f)[1]
                    frame_input = pub.replace(".exr", ".%04d{}".format(ext))

            return self.get_video_buffer(frame_input, sf), "webm"

        # alright now what's left? playblast & render are taken care of
        # 2d & export are left.
        elif data["type"] == "2D":
            with open(pub, "rb") as f:
                buf = io.BytesIO(f.read())
            ext = os.path.splitext(pub)[-1].lstrip(os.extsep)
            return buf, ext

        # at this point, what to attach is a bit of a toss-up.
        # see if they want to attach a snapdraw, otherwise nothing
        if snapdraw:
            res = QMessageBox.question(None, "Publish Attachment",
                                       "No attachment found for export {}.\nWant to take a pretty picture?".format(data["task"]))
            if res == QMessageBox.Yes:
                # how to minimize all prism stuff?
                # main_win = self.core.messageParent
                # if main_win:
                #     print(main_win.windowTitle())

                wins = dict((w, w.isVisible()) for w in (self.core.sm, self.core.pb))
                for w in wins:
                    w.hide()
                buf = snapdraw.main()
                for w, v in wins.items():
                    w.setVisible(v)

                return buf, "png"
        else:
            QMessageBox.warning(None, "Dependencies Error",
                                "Python dependencies for screenshot tool are not set up! Yell at your TD.")

        return None, None


    def get_video_buffer(self, input_path, start_frame=None, maxSize=8000000, fmt="webm"):
        """
        Take an image sequence and make it a webm of limited size.
        :param input_path: start image/mp4 for ffmpeg frames to movie
        :param start_frame: initial frame number
        :param maxSize: HARD limit. could attempt a target size later but meh.
        :param fmt: string format - extension without leading .
        :return: byte buffer
        """
        ffmpegIsInstalled = False
        if platform.system() == "Windows":
            ffmpegPath = os.path.join(self.core.prismRoot, "Tools", "FFmpeg", "bin", "ffmpeg.exe")
            if os.path.exists(ffmpegPath):
                ffmpegIsInstalled = True
        elif platform.system() == "Linux":
            ffmpegPath = "ffmpeg"
            try:
                subprocess.Popen([ffmpegPath])
                ffmpegIsInstalled = True
            except:
                pass
        elif platform.system() == "Darwin":
            ffmpegPath = os.path.join(self.core.prismRoot, "Tools", "ffmpeg")
            if os.path.exists(ffmpegPath):
                ffmpegIsInstalled = True
        else:
            ffmpegPath = ""

        if not ffmpegIsInstalled:
            QMessageBox.critical(self.core.messageParent, "Video conversion", "Could not find %s" % ffmpegPath)
            return

        args = [ffmpegPath]
        if start_frame:
            # this only happens for frame input, as those pass in start frame
            # these args cause errors for video input
            args.extend(["-framerate", "24",
                         "-start_number", start_frame,])
        args.extend(["-apply_trc", "iec61966_2_1",
                     "-i", input_path,
                     # "-c:v", "libvpx-vp9",
                     "-b:v", "512k",
                     "-f", fmt,
                     "-pix_fmt", "yuva420p",
                     "-fs", str(maxSize),
                     "-"
        ])

        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        buf = io.BytesIO(process.communicate()[0])
        return buf
