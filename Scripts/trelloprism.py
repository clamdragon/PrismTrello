import os, subprocess, json
import requests, ssl
from tempfile import gettempdir
import trelloqt

"""
Shit for connecting to Trello - syncing and posting to cards.
"""

class Unauthorized(Exception):
    # Simple exception to raise for 401 response
    pass


class NotFound(Exception):
    # Another one for 404
    pass


class TrelloHandler(object):
    token_url = "https://trello.com/1/authorize?expiration=never&name={n}&scope=read,write&response_type=token&key={k}"
    template_boards = {"assets": "5c6de1f362df495355f996de",
                       "shots": "5c6de2088ac2313d84bb765b"}

    def __init__(self, core):
        self.core = core
        self.project_data = trelloqt.get_project_config(core, ("api_key", "team_url"))
        self.team_id = self.project_data["team_url"].split("/")[3]
        # self.client, self.team_id = self._connect()
        self.session = requests.session()
        self.is_connected = self._connect()
        # error it
        assert self.is_connected
        # self.board_data = self.get_board_data()
        self.task_paths = {"Export": "Export",
                           "2D": os.path.join("Rendering", "2dRender"),
                           "Playblast": "Playblasts",
                           "Render": os.path.join("Rendering", "3dRender"),
                           "External": os.path.join("Rendering", "external")}


    def _connect(self):
        """
        Connect to Trello and return valid client and list of boards (assets & shots)
        :return: bool, whether the connection was successful
        """
        try:
            requests.get("http://www.google.com")
        except requests.ConnectionError:
            return False

        api_key = self.project_data["api_key"]
        # team_name = validate_string(self.project_data["team_name"])
        # team_url = "".join(self.project_data["team_name"].split()).lower()
        token = self.core.getConfig(self.core.projectName, "trello_token")
        self.session.params = {"key": api_key,
                               "token": token,}
        self.session.headers = {"Accept": "application/json",}
                                # "Content-Type": "application/json; charset=utf-8",}

        try:
            # ALL fields for each board in the team
            self.send("GET", "organizations/{}/boards".format(self.team_id))
        except Unauthorized:
            app_name = self.core.projectName
            self.session.params["token"] = self._get_new_token(api_key, app_name)
            try:
                self.send("GET", "organizations/{}/boards".format(self.team_id))
            except Unauthorized:
                return False

        return True


    def _get_new_token(self, api_key, app_name):
        """
        Get a new user token from Trello. Open popup for user to authorize app.
        :return: string - user token
        """
        url = self.token_url.format(n=app_name, k=api_key)
        # webbrowser.open_new(url)

        label = "<a href='{}'>Click here to authorize Trello</a>, then " \
                "enter the generated token (the gibberish):".format(url)
        token_dialog = trelloqt.LinkDialog(label)
        token_dialog.setWindowTitle("Authorization required")
        result = token_dialog.exec_()
        if result:
            token = token_dialog.get_text().strip()
            self.core.setConfig(self.core.projectName, "trello_token", token)
            return token
        else:
            raise ValueError("User token missing for Trello connection!")


    def _purge_token(self):
        """
        Remove the user token from user's prefs file.
        :return: None
        """
        self.core.setConfig(self.core.projectName, "trello_token", "")


    def _purge_project_data(self):
        """
        Remove trello data from the project prefs file.
        :return: None
        """
        for k in ("api_key", "team_url"):
            self.core.setConfig("trello", k, "", configPath=self.core.prismIni)


    def validate_string(self, s):
        """
        Remove all whitespace and CamelCase the given string.
        :param s: raw input string with whitespace and whatever for caps
        :return: Prism friendly version of the string
        """
        return self.core.validateStr("".join(w[0].upper()+w[1:] for w in s.split()))


    def send(self, method, uri, **kwargs):
        """
        Convenience function to take care of errors & ensuring right types.
        Also re-routes to subroutine if SSL version doesn't support https.
        Fucking OSX. Fucking Maya.
        :param method: "GET", "PUT", "POST", "DELETE"
        :param uri: the trello endpoint
        :param kwargs: any params for the request
        :return: json of the specified trello object
        """
        url = "https://api.trello.com/1/{}".format(uri.lstrip("/"))
        req = self.session.prepare_request( requests.Request(method, url, **kwargs) )
        print "KWARGS: "+str(kwargs.get("files"))
        print "REQUEST: " + str(req)

        if not hasattr(ssl, "PROTOCOL_TLSv1_2"):
        # if True:
            # send as a cURL subprocess.
            print "NO PROTOCOL"
            code, content = self.curl_send(method, req.url, kwargs.get("files"))
            print "CONTENT: " + str(content)
        else:
            print "HAVE PROTOCOL"
            r = self.session.send(req)
            code, content = r.status_code, r.content

        if code == 401:
            raise Unauthorized(content)
        elif code == 404:
            raise NotFound(content)
        elif code != 200:
            # result.raise_for_status()
            raise requests.HTTPError(content)
        else:
            # return result.json()
            return json.loads(content)


    def curl_send(self, method, url, files):
        """
        Send the HTTPS trello request via cURL in a subprocess.
        :param method: HTTP method of the request
        :param url: the pre-encoded URL (thanks requests)
        :param files: a dict of {"file": (name, contents)} or None
        :return: trello json data
        """
        if files:
            # requests takes files as name, binary string
            # but curl needs a filename - so make one
            name, bytestr = files["file"]
            print "NAMEEE "+str(name)
            fn = os.path.join(gettempdir(), name)
            with open(fn, "wb") as of:
                of.write(bytestr)
            curl_args = ["--form", "file=@{}".format(fn), "--url", url]
        else:
            fn = os.path.join(gettempdir(), "prism")
            curl_args = ["--form", "file=@{}".format(fn),"--url", url]

        # subprocess needs command as a list that is basically split along whitespace
        curl_args = ["curl", "-s", "-o", fn, "-w", "%{http_code}",
                     "--request", method] + curl_args
        print "CURL ARGS: "+ str(curl_args)

        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            # set startup invisible flag
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        # open subprocess pipe and get its return value, which oughta be a json-loadable string
        response = subprocess.check_output(curl_args, startupinfo=startupinfo)
        with open(fn) as of:
            content = of.read()

        # calling method takes care of HTTP error handling
        return int(response), content


    def batch_get(self, queries):
        """
        Reject empty query list (edge case of a team with 0 boards)
        :param queries: list of trello endpoints to be joined together into a batch request
        :return: big ol' list of dicts, len(result) = len(queries) & queries[i] -> result[i]
        then its response code is a key for accessing the json data from the endpoint
        """
        if not queries:
            return []
        batch_url = "/batch?urls={}"
        return self.send("GET", batch_url.format(",".join(queries)))


    def get_board_data(self):
        """
        Batch get for ALL data on the Trello team at once. Batching majorly reduces HTTP traffic.
        :return: large dict of Trello json info, massaged slightly so it's nested to have
        board["lists"], list["cards"], card["customFieldItems"]
        """
        boards = self.send("GET", "organizations/{}/boards".format(self.team_id))
        batch_paths = ["/board/{}/lists/open",
                      "/boards/{}/customFields",
                      "/board/{}/cards/open?customFieldItems=true",
                      "/boards/{}/cards/open?attachments=true",]
                      # "/boards/{}/checklists",]

        # form is clustered by board, ie:
        # board1.lists, board1.cards, board2.lists, board2.cards, etc
        board_urls = [uri.format(b["id"]) for b in boards for uri in batch_paths]
        all_data = self.batch_get(board_urls)
        data = {"assets": [], "shots": [], "other": []}
        # step by four (or number of batch paths)
        step = len(batch_paths)
        for i, board_data in enumerate(boards):
            i *= step
            board_data["lists"] = all_data[i].get("200")
            for l in board_data["lists"]:
                l["cards"] = []
            board_data["customFields"] = all_data[i+1].get("200")

            # outermost loop is cards
            for n, c in enumerate(all_data[i+2].get("200")):
                # c["checklists"] = []
                # for cl in all_data[i+3].get("200"):
                #     if cl["idCard"] == c["id"]:
                #         c["checklists"].append(cl)
                # card order is the same. merge. i+2 is custom fields, i+3 is attachments
                c.update(all_data[i+3].get("200")[n])

                for cf in c["customFieldItems"]:
                    for cf_def in board_data["customFields"]:
                        # find the right definition
                        if cf["idCustomField"] == cf_def["id"]:
                            # assign name and list value if necessary
                            cf["name"] = cf_def["name"]
                            if cf_def["type"] == "list":
                                # get value from cf_def
                                cf["value_dict"] = dict((o["id"], o["value"]) for o in cf_def["options"])

                for l in board_data["lists"]:
                    if c["idList"] == l["id"]:
                        l["cards"].append(c)

            # separate into sectors
            bg = board_data["prefs"]["background"]
            if bg == "purple":
                data["assets"].append(board_data)
            elif bg == "orange":
                data["shots"].append(board_data)
            else:
                data["other"].append(board_data)

        return data


    def get_task_dict(self, board):
        """
        Return an option id: value mapping of the task dict
        :param board: board json to lookup ids on
        :return:
        """
        for cf in board["customFields"]:
            if cf["name"] == "Type":
                return dict((item["id"], item["value"]["text"]) for item in cf["options"])
        else:
            return {}


    def sync_from_prism(self, set_max_func, increment_func):
        """
        Sync Trello boards to match Prism directory structure.
        Asset categories are joined using "/" for Trello board names.
        :param set_max: function from parent to set maximum value
        :param increment: function from parent to signal progress
        :return:
        """
        data = self.get_board_data()
        ap = self.core.getAssetPath()
        sp = self.core.getShotPath()

        # asset_paths = self.core.getAssetPaths()
        asset_paths = self.core.getAssetPath()
        shot_paths = [sd for sd in os.listdir(sp) if os.path.isdir(os.path.join(sp, sd))]
        set_max_func(len(asset_paths) + len(shot_paths))

        # start with assets - get all of them and
        for asset_dir in asset_paths:
            config = os.path.join(asset_dir, "entityinfo.ini")

            category = os.path.relpath(os.path.dirname(asset_dir), ap).replace(os.path.sep, "/")
            entity = os.path.basename(asset_dir)

            # get_* functions CREATE the board/list if it doesn't exist
            b = self.get_category_board(data["assets"], "assets", category)
            l = self.get_entity_list(b, entity)
            self.core.setConfig("trello", "board_id", b["id"], configPath=config)
            self.core.setConfig("trello", "list_id", l["id"], configPath=config)

            increment_func()

        for sd in os.listdir(sp):
            shot_dir = os.path.join(sp, sd)
            config = os.path.join(shot_dir, "entityinfo.ini")
            category, entity = sd.split("-", 1)

            b = self.get_category_board(data["shots"], "shots", category)
            l = self.get_entity_list(b, entity)
            self.core.setConfig("trello", "board_id", b["id"], configPath=config)
            self.core.setConfig("trello", "list_id", l["id"], configPath=config)

            increment_func()


    def sync_from_trello(self, set_max_func, increment_func):
        """
        Sync Prism dirs to match Trello boards.
        Nested categories are not supported.
        :param set_max: function from parent to set maximum value
        :param increment: function from parent to signal progress
        :return: None
        """
        data = self.get_board_data()
        ap = self.core.getAssetPath()
        sp = self.core.getShotPath()

        # total number of entities
        set_max_func(sum(len(b["lists"]) for b in data["shots"]) +
                     sum(len(b["lists"]) for b in data["assets"]))

        for pipe, path in (("assets", ap), ("shots", sp)):
            for board in data[pipe]:
                if "template" in board["name"].lower():
                    for _ in board["lists"]: increment_func()
                    continue

                # pprint(board)
                # bn = self.validate_string(board["name"])
                if pipe == "assets":
                    # this is the only way to support nested categories - split now
                    # and rejoin, including formattable spot at the end for entity
                    cats = [self.validate_string(c) for c in board["name"].split("/")] + ["{}"]
                    cat_path = os.path.join(path, *cats)
                elif pipe == "shots":
                    cat = self.validate_string(board["name"])
                    cat_path = os.path.join(path, "{}-{}".format(cat, "{}"))
                else:
                    # get the linter to shut up
                    return

                task_type_dict = self.get_task_dict(board)
                for l in board["lists"]:
                    ln = self.validate_string(l["name"])
                    basepath = cat_path.format(ln)

                    if not os.path.exists(basepath):
                        for x in ("Export", "Playblasts", "Rendering", "Scenefiles"):
                            os.makedirs(os.path.join(basepath, x))

                    config = os.path.join(basepath, "entityinfo.ini")
                    self.core.setConfig("trello", "board_id", board["id"], configPath=config)
                    self.core.setConfig("trello", "list_id", l["id"], configPath=config)

                    for c in l["cards"]:
                        self.get_dir_for_card(basepath, c, task_type_dict)

                    increment_func()


    def get_dir_for_card(self, basepath, card_json, task_types):
        """
        Get the task directory of given card.
        :param basepath: asset/shot path
        :param card_json: data from trello api
        :param task_types: dict of parent board, to get custom field value
        :return: task path
        """
        try:
            task_type = next(
                cf for cf in card_json["customFieldItems"] if cf["name"] == "Type")
        except StopIteration:
            print("Untyped task {}".format(card_json["name"]))
            return

        task_path = self.task_paths[task_types[task_type["idValue"]]]
        task_name = self.validate_string(card_json["name"])
        task_path = os.path.join(basepath, task_path, task_name)
        if not os.path.exists(task_path):
            os.makedirs(task_path)
            config = os.path.join(task_path, "taskinfo.ini")
            self.core.setConfig("trello", "id", card_json["id"], configPath=config)

        return task_type


    def publish_to_card(self, data):
        """
        Push the publish data to Trello! Includes ensuring board/list/card exists,
        saving its ID for later easy access, bumping the list + card, updating desciption,
        and adding any attachments.
        :param data: dict - the formatted publish data
        :return: None
        """
        board_data = self.get_board_data()[data["pipe"]]
        card, card_id = self.get_card(board_data, data)

        # BEGIN CARD EDITS
        # bump the list
        self.send("PUT", "lists/{}".format(card["idList"]), params={"pos": "top"})

        # change description
        # prism publish info designated by ### tag
        d = card["desc"]
        desc = ["###{} by {}\n###{}".format(data["version"], data["author"], data["comment"])]
        lines = d.split("\n")
        for l in lines:
            if not l.startswith("###"):
                desc.append(l)
        desc = "\n".join(desc)
        data["description"] = desc
        data["trello_url"] = card["url"]

        put_args = {"desc": desc,
                    "pos": "top",
                    "subscribed": "true"}
        # PUT updated descriptions
        self.send("PUT", "cards/{}".format(card_id), params=put_args)

        # leave a comment or attachment - that's another POST request each
        # first: determine if there is an image/video to attach
        if data["attach"]:
            # format for attachment type
            latest = "LatestVersion.{}".format(data["attach_type"])
            prev = "PreviousVersion.{}".format(data["attach_type"])
            # DELETE previous version if it exists, and rename old latest to previous.
            for a in card["attachments"]:
                if a["name"] == prev:
                    self.send("DELETE", "cards/{}/attachments/{}".format(card_id, a["id"]))
                elif a["name"] == latest:
                    self.send("PUT", "cards/{}/attachments/{}".format(card_id, a["id"]), params={"name": prev})

            # ADD NEW attachment
            files = {"file": (latest, data["attach"].getvalue())}
            self.send("POST", "cards/{}/attachments".format(card_id), files=files)

        b = next(b for b in board_data if b["id"] == card["idBoard"])
        # PUT custom fields if necessary
        for cf in b["customFields"]:
            for cf_name, text_value in ("Status", "Review Needed"), ("Type", data["type"]):
                if cf_name == cf["name"]:
                    option_id = next(item["id"] for item in cf["options"] if item["value"]["text"] == text_value)
                    # curr_val = next(ccf["value"] for ccf in card["customFieldItems"] if ccf["id"] == cf["id"])
                    self.send("PUT", "card/{}/customField/{}/item".format(card_id, cf["id"]),
                              params={"idValue": option_id})
                    break


    def get_card(self, board_data, publish_data):
        """
        Guaranteed GET of a Trello card - whether there is a saved ID that is good or bad,
        or if no task or entity or even category exists on Trello.
        :param data: dict - the publish data
        :param board_data: dict - Trello json
        :return:
        """
        config = os.path.join(publish_data["task_path"], "taskinfo.ini")
        card_id = self.core.getConfig("trello", "id", configPath=config)
        if not card_id:
            card = self.ensure_card_exists(board_data, publish_data)
            card_id = card["id"]
            self.core.setConfig("trello", "id", card_id, configPath=config)
        else:
            try:
                card = self.send("GET", "cards/{}".format(card_id),
                                 params={"customFieldItems": "true", "attachments": "true"})
            except NotFound:
                # it's possible that the saved ID is no longer valid.
                # try to re-find / re-create it.
                card = self.ensure_card_exists(board_data, publish_data)
                card_id = card["id"]
                self.core.setConfig("trello", "id", card_id, configPath=config)

        return card, card_id


    def ensure_card_exists(self, board_data, publish_data):
        """
        Get card for this publish from given trello data.
        If anything doesn't exist, make it.
        :param board_data: json of nested trello data
        :param publish_data: data squeezed out of the filepaths of the publish
        :return:
        """
        b = self.get_category_board(board_data, publish_data["pipe"], publish_data["category"])
        l = self.get_entity_list(b, publish_data["entity"])

        task = publish_data["task"].lower()
        try:
            c = next(c for c in l["cards"] if task == self.validate_string(c["name"]).lower())
        except StopIteration:
            new_card = {"name": publish_data["task"],
                        "idList": l["id"]}
            c = self.send("POST", "cards/", params=new_card)
            # gotta re-get 'cause, again, posting doesn't return attachments & custom fields
            c = self.send("GET", "cards/{}".format(c["id"]),
                             params={"customFieldItems": "true", "attachments": "true"})
            l["cards"].append(c)

        return c


    def get_category_board(self, board_data, pipe, category):
        """
        Conveniece function to guaranteed get board json.
        Tries to find by name lookup but creates a new board if there is no match.
        Looks to cloud templates for easy copying.
        :param board_data: big ol' dict (only for this pipe tho)
        :param pipe: assets or shots - affects which template board is copied
        :param category: name of the board, with any subcategories joined Trello style (by "/")
        :return: board json dict
        """
        # template_id = next(t["id"] for t in board_data if "template" in t["name"].lower())
        # data is compared as LOCAL - because we can't UNVALIDATE the string
        # validate trello string(s) and compare the lowers
        valid_bname = lambda bn: "/".join((self.validate_string(c) for c in bn.split("/"))).lower()
        try:
            b = next(b for b in board_data if valid_bname(b["name"]) == category.lower())
        except StopIteration:
            # if no match is found... make a new board
            new_board = {"name": category,
                         "idOrganization": self.team_id,
                         "idBoardSource": self.template_boards[pipe],
                         "prefs_permissionLevel": "org", }
            b = self.send("POST", "boards/", params=new_board)
            # posting it doesn't return all the board info sometimes, so get it all here if necessary
            b = self.send("GET", "boards/{}?lists=open&customFields=true".format(b["id"]))
            # scrub template lists
            for l in b["lists"]: self.send("PUT", "lists/{}/closed?value=true".format(l["id"]))

            board_data.append(b)

        return b


    def get_entity_list(self, board, entity):
        """
        Get the Trello json for the given entity on the given board.
        Creates if it doesn't exist.
        :param board: board json dict
        :param entity: name of the asset/shot
        :return: list json dict
        """
        try:
            l = next(l for l in board["lists"] if self.validate_string(l["name"]).lower() == entity.lower())
        except StopIteration:
            new_list = {"name": entity,
                        "idBoard": board["id"], }
            l = self.send("POST", "lists/", params=new_list)
            l["cards"] = []
            board["lists"].append(l)

        return l
