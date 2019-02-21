PrismTrello is a plugin for the <a href="https://prism-pipeline.com/">prism pipeline</a> tool for 3D animation.
PrismTrello links your Prism project to a Trello team for task tracking, review, and discussion.
The marriage works because Trello functions well as a top-down and collaborative space while Prism ensures your team is all working on and talking about the right stuff.

AKA Poor Man's Shotgun.

To set up for your Prism project:
Put the "PrismTrello" folder in (or clone repo into) your Prism project's "Plugins" directory.
Prism should detect and load it automatically.
Enable it & sync to your Trello team in the Prism settings window.

Categories/sequences synced from Prism to Trello create boards with certain necessary attributes.
To manually create boards that fit the PrismTrello format, copy from these templates for <a href=https://trello.com/b/b1ErgFdB>assets</a> and <a href=https://trello.com/b/vliQo2PD>shots</a>.

One time set-up needs a team admin's <a href="https://trello.com/app-key/">api key</a> and your Trello team URL.
Team members then authorize the tool the first time they use it. All of this is done via popup prompt.

If you want to use the bundled screenshot/annotation tool (recommended!), use pip to install the following modules to a path visible to Prism (likely your Prism project's CustomModules directory):
- qimage2ndarray
- mss
- pypng
