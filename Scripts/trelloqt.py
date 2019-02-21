try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except ImportError:
    from PySide.QtCore import *
    from PySide.QtGui import *
import webbrowser


class LinkDialog(QDialog):
    """
    Custom dialog because standard input dialog
    doesn't allow hyperlinks, the fucking shitty thing.
    """
    def __init__(self, text=""):
        super(LinkDialog, self).__init__()
        self.setModal(True)
        l = QVBoxLayout()
        self.setLayout(l)
        self.label = QLabel(text, self)
        self.label.setOpenExternalLinks(True)
        l.insertWidget(0, self.label)
        self.edit = QLineEdit(self)
        l.insertWidget(1, self.edit)
        b = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        b.accepted.connect(self.accept)
        b.rejected.connect(self.reject)
        l.insertWidget(2, b)

    def get_text(self):
        return self.edit.text()


class TrelloSettingsUi(QGroupBox):
    template_urls = {"assets": "https://trello.com/b/b1ErgFdB",
                     "shots": "https://trello.com/b/vliQo2PD"}
    """
    Object which is put into the project tab of Prism settings
    to control Trello integration.
    """
    def __init__(self, core, parent):
        super(TrelloSettingsUi, self).__init__(parent)
        self.setCheckable(True)
        self.setTitle("Trello Integration")
        saved_state = core.getConfig("trello", "enabled", configPath=core.prismIni) or "False"
        self.setChecked(eval(saved_state))
        save_check = lambda s: core.setConfig("trello", "enabled", s, configPath=core.prismIni)
        self.toggled.connect(save_check)
        layout = QHBoxLayout(self)
        self.setLayout(layout)

        def open_template(pipe):
            def func(*args):
                webbrowser.open_new_tab(self.template_urls[pipe])
            return func
        # shotcut to the template boards online
        self.templates_button = QPushButton("Template Boards")
        self.template_menu = QMenu(self)
        self.template_menu.addAction("Assets (Board = Category)", open_template("assets"))
        self.template_menu.addAction("Shots (Board = Sequence)", open_template("shots"))
        self.templates_button.setMenu(self.template_menu)
        layout.addWidget(self.templates_button)

        self.sync_down_button = QPushButton("Sync Trello -> Prism", self)
        self.sync_down_button.setToolTip("Get new data from Trello and create in Prism project.")
        layout.addWidget(self.sync_down_button)
        self.sync_up_button = QPushButton("Sync Prism -> Trello", self)
        self.sync_up_button.setToolTip("Get data from Prism project and push to Trello team.")
        layout.addWidget(self.sync_up_button)


def get_project_config(core, keys, proj="trello"):
    """
    Get all of the .ini saved variables needed to interact with plugin.
    If they don't exist, get them via dialog.
    :args: list of strings
    :return: a dict of the string keys : config values
    """
    data = {}
    n = proj.title()
    for k in keys:
        v = core.getConfig(proj, k, configPath=core.prismIni)
        if not v:
            win = QInputDialog()
            win.setWindowTitle("{} data required!".format(n))
            win.setLabelText("{} {} missing! Enter here, or contact your technical director.".format(n, k))
            result = win.exec_()
            if result:
                v = win.textValue().strip()
                core.setConfig(proj, k, v, configPath=core.prismIni)
            else:
                raise ValueError("{} missing for {} connection!".format(k, n))

        data[k] = v

    return data
