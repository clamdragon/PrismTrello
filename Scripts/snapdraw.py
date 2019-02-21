import sys, os
from io import BytesIO
from collections import deque
try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except ImportError:
    from PySide.QtCore import *
    from PySide.QtGui import *

import qimage2ndarray as q2n
import numpy, mss, png

# THIS VERSION IS MODIFIED TO NOT USE PIL
# INSTEAD USE MSS, NUMPY & PNG TO KEEP IT PURE

"""
snapdraw.py - a simple tool much like the Snipping Tool in windows,
only multiplatform, a bit simpler, and easily integratable into other python apps.
Use it like so:
ScreenshotOverlay is for getting a PIL screen grab image from drag area.
AnnotationWindow is for editing any PIL image, and gives control back to
calling frame when finished or cancelled. AnnotationWindow.final_img is result.
Or call main() to just run it in normal configuration and get PIL image result. 
"""

class ScreenshotOverlay(QDialog):
    """
    A UI for taking mouse-drag area screenshots. Just a partially
    transparent dialog that covers the whole screen. When user mouse drags,
    the target area is masked and made fully transparent.
    Esc to quit, Enter/Return to accept and screengrab selected area. Image saved to self.img.
    """
    def __init__(self, parent=None):
        self.base = super(ScreenshotOverlay, self)
        self.base.__init__(parent)
        screen = QApplication.desktop().screenGeometry(parent or 0)
        screen_width, screen_height = screen.size().toTuple()
        self.setGeometry(0, 0, screen_width, screen_height)
        self.setStyleSheet("background-color: black;")
        self.setWindowOpacity(0.5)

        self.start = QPoint()
        self.end = QPoint()
        self.bbox = (0, 0, screen_width, screen_height)
        self.img = None

    def mousePressEvent(self, event):
        """
        Initialize a new drag area, position-wise and appearance wise
        :param event:
        :return:
        """
        self.start = event.pos()
        self.end = self.start
        self.clearMask()
        self.update()
        event.accept()

    def mouseMoveEvent(self, event):
        """
        Event is only sent when a mouse button is pressed.
        Update selected area and draw the mask.
        :param event:
        :return:
        """
        self.end = event.pos()

        # visualize screengrab area by masking out the overlay -
        # so user can see EXACTLY what it will look like.
        mask = QPixmap(self.size())
        p = QPainter()
        p.begin(mask)
        p.setPen(Qt.white)
        p.setBrush(Qt.white)
        p.drawRect(QRect(self.start, self.end))
        p.end()

        self.setMask(mask)
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event):
        """
        Save the area as a PIL-friendly bounding box (no negative height/width)
        :param event:
        :return:
        """
        x1 = min(self.start.x(), self.end.x())
        y1 = min(self.start.y(), self.end.y())
        x2 = max(self.start.x(), self.end.x())
        y2 = max(self.start.y(), self.end.y())

        self.bbox = (x1, y1, x2, y2)
        event.accept()

    def keyPressEvent(self, event):
        """
        Watch for Esc/enter to reject/accept.
        :param event:
        :return:
        """
        k = event.key()
        if event.matches(QKeySequence.Quit) or k == Qt.Key_Escape:
            # self.close()
            self.reject()
            return True
        elif k == Qt.Key_Enter or k == Qt.Key_Return:
            # this is the good one. take the screenshot and pass it along.
            self.hide()
            with mss.mss() as sct:
                self.img = numpy.array(sct.grab(self.bbox))
            self.accept()
            return True
        else:
            return self.base.keyPressEvent(event)


class AnnotationWindow(QDialog):
    """
    The window for an ImageCanvas. Includes toolbar for pen switching,
    as well as I/O operations for discard/save/accept.\
    The drawing canvas (with the image) is its own object: self.canvas.
    """
    def __init__(self, img=None, parent=None):
        """
        Create layout, toolbar & actions for pen switching/IO.
        Create canvas if img  is passed.
        :param img: (optional) PIL image for optional auto-opening
        :param parent: QObject parent.
        """
        self.base = super(AnnotationWindow, self)
        self.base.__init__(parent)
        self.canvas = None
        self.final_img = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)
        self.setWindowTitle("Annotate Screenshot")
        self.setWindowFlags(Qt.Window)
        self.setModal(False)
        toolbar = QToolBar(self)
        toolbar.setMovable(False)
        toolbar.layout().setSpacing(8)
        toolbar.layout().setContentsMargins(4, 4, 4, 4)
        layout.addWidget(toolbar)

        self.pens_grp = QActionGroup(toolbar)

        # different pens
        icon_pix = QPixmap(8, 8)
        for color in (Qt.red, Qt.blue, Qt.green, Qt.darkMagenta, Qt.white):
            icon_pix.fill(color)
            s = "{} Pen".format(str(color).split(".")[-1].title())
            pen_action = self.pens_grp.addAction(toolbar.addAction(QIcon(icon_pix), s))
            pen_action.setData(QPen(color, 2, c=Qt.RoundCap))
            pen_action.setCheckable(True)

        icon_pix = QPixmap(16, 16)
        hilite_color = QColor.fromRgbF(.9, 1, .1, .2)
        icon_pix.fill(hilite_color)
        hilite_action = self.pens_grp.addAction(toolbar.addAction(
            QIcon(icon_pix), "Highlighter"))
        hilite_action.setData(QPen(hilite_color, 36, c=Qt.RoundCap))
        hilite_action.setCheckable(True)

        eraser_action = self.pens_grp.addAction(toolbar.addAction(
            self.style().standardIcon(QStyle.SP_DialogNoButton), "Eraser"))
        eraser_action.setData(QPen(Qt.transparent, 36, c=Qt.RoundCap))
        eraser_action.setCheckable(True)

        self.pens_grp.triggered.connect(self.set_canvas_pen)

        # I/O actions
        sep = QWidget(toolbar)
        sep.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(sep)
        cancel_action = toolbar.addAction(
            self.style().standardIcon(QStyle.SP_DialogCancelButton), "Cancel")
        cancel_action.triggered.connect(self.reject)
        save_action = toolbar.addAction(
            self.style().standardIcon(QStyle.SP_DialogSaveButton), "Save")
        save_action.triggered.connect(self.save_img)
        finish_action = toolbar.addAction(
            self.style().standardIcon(QStyle.SP_DialogApplyButton), "Finish")
        finish_action.triggered.connect(self.finish_img)

        if img.any():
            self.set_image(img)

    def set_image(self, img):
        """
        Create a new canvas for the given img and add to Annotator.
        Any previous canvas is abandoned.
        :param img: PIL image to load
        :return:
        """
        layout = self.layout()
        # TODO perhaps a scroll area?
        if self.canvas:
            layout.removeWidget(self.canvas)
            self.canvas.close()
        self.canvas = ImageCanvas(img, self)
        layout.addWidget(self.canvas)
        layout.setAlignment(self.canvas, Qt.AlignLeft | Qt.AlignTop)
        # self.setCentralWidget(self.canvas)
        # set default pen (red)
        self.pens_grp.actions()[0].trigger()
        self.adjustSize()

    def set_canvas_pen(self, action):
        """
        Slot for all pen buttons. Each action object stores its QPen as data.
        They are in an action group so only one can be checked.
        :param action: the action corresponding to the desired pen.
        :return:
        """
        if self.canvas:
            self.canvas.pen = action.data()
            action.setChecked(True)

    def save_img(self):
        """
        Save the combined image in the current canvas to disk.
        :return:
        """
        if self.canvas:
            img = self.canvas.get_final_image()
            out_path = QFileDialog.getSaveFileName(
                caption="Save Annotated Snapshot", dir=os.path.expanduser("~"),
                filter="*.png", selectedFilter="*.png")[0]
            if out_path:
                # png needs it converted into 2D array
                f = numpy.reshape(img, (-1, img.shape[1] * img.shape[-1]))
                png.from_array(f, "RGBA;8").save(out_path)
                # ext = os.path.splitext(out_path)[-1]
                # QMessageBox.information(self, "Saved!", "Saved!")
                # if ext == ".jpg":
                #     img.save(out_path, format="JPEG", optimize=True)
                # elif ext == ".bmp":
                #     img.save(out_path, format="BMP", optimize=True)
                # elif ext == ".png":
                #     img.save(out_path, format="PNG", optimize=True, quality=100)
                # else:
                #     raise IOError("Invalid file extension.")

    def finish_img(self):
        """
        Get the final image from the canvas and set this dialog to accepted.
        Returns function flow back to calling frame.
        :return:
        """
        if self.canvas:
            self.final_img = self.canvas.get_final_image()
            self.accept()
        else:
            self.reject()

    def keyPressEvent(self, event):
        """
        Watch for UNDO keystroke, pass along to canvas.
        :param event: QKeyEvent - info about key press
        :return:
        """
        if event.matches(QKeySequence.Undo) and self.canvas:
            self.canvas.undo()
            return True
        else:
            return self.base.keyPressEvent(event)


class ImageCanvas(QWidget):
    """
    Given an image, creates a Qt canvas object which allows drawing on that image.
    Display is actually two images stacked on top of each other.
    Use .get_final_img() to get merged PIL image.
    Maintains an undo stack 20 items deep.
    """
    def __init__(self, img, parent=None):
        self.base = super(ImageCanvas, self)
        self.base.__init__(parent)
        self.orig_img = img
        # w, h = img.size
        h, w = img.shape[0:2]
        l = QGridLayout(self)
        l.setContentsMargins(0, 0, 0, 0)
        self.bg = QLabel(self)
        self.bg.setFixedSize(w, h)
        self.canvas = QLabel(self)
        self.canvas.setFixedSize(w, h)
        l.addWidget(self.bg, 0, 0)
        l.addWidget(self.canvas, 0, 0)
        self.bg.stackUnder(self.canvas)

        # LAYERS of images.
        # base layer is original screenshot,
        # overlay is the drawing canvas and they will be merged via PIL
        # on save/finish
        self.bg_img = q2n.array2qimage(img).rgbSwapped()
        self.bg.setPixmap(QPixmap.fromImage(self.bg_img))
        overlay = QPixmap(w, h)
        overlay.fill(Qt.transparent)
        self.canvas_img = overlay.toImage()

        self.pen = QPen()
        self.painter = QPainter()
        self.prev_pos = QPoint()
        self.undo_stack = deque(maxlen=20)

    def updateImage(self):
        """
        Update the drawing canvas with a pixmap of the current QImage
        :return:
        """
        self.canvas.setPixmap(QPixmap.fromImage(self.canvas_img))

    def get_final_image(self):
        """
        Simple merge operation - just splat the annotation layer on top of
        original image. That's what is displayed, so it should be fine.
        :return: pillow Image
        """
        # img = fromqimage(self.bg_img)
        # annotations = fromqimage(self.canvas_img)
        # img.paste(annotations, mask=annotations)
        # OR: convert to RGBA and .alpha_composite
        # but this is good enough!
        merged = QImage(self.bg_img.size(), QImage.Format_ARGB32_Premultiplied)
        p = QPainter()
        p.begin(merged)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        p.drawImage(0, 0, self.bg_img)
        p.drawImage(0, 0, self.canvas_img)
        p.end()
        return q2n.byte_view(merged.rgbSwapped())
        # return q2n.rgb_view(merged.rgbSwapped())

    def undo(self):
        """
        Pop the top QImage from the undo stack and set canvas.
        :return:
        """
        try:
            self.canvas_img = self.undo_stack.pop()
        except IndexError:
            print("Undo stack exhausted!")
        else:
            self.updateImage()

    def mousePressEvent(self, event):
        """
        Begin a new drawing operation. Save Qimage as it currently exists to undo stack.
        Draw an ellipse so even single clicks cause paint.
        :param event:
        :return:
        """
        self.undo_stack.append(self.canvas_img.copy())
        self.prev_pos = event.pos()
        self.painter.begin(self.canvas_img)
        self.painter.setPen(self.pen)
        self.painter.setCompositionMode(QPainter.CompositionMode_Source)
        self.painter.drawPoint(self.prev_pos)
        self.painter.end()

        self.updateImage()
        event.accept()

    def mouseMoveEvent(self, event):
        """
        Perform drawing using QPainter.
        TODO: modifiers & options for drawing straight lines/arrows/shapes?
        :param event:
        :return:
        """
        pos = event.pos()
        self.painter.begin(self.canvas_img)
        self.painter.setPen(self.pen)
        self.painter.setCompositionMode(QPainter.CompositionMode_Source)
        self.painter.drawLine(self.prev_pos, pos)
        self.painter.end()

        self.prev_pos = pos

        self.updateImage()
        event.accept()

    def enterEvent(self, event):
        """
        Set cursor to reflect what the current pen is.
        :param event:
        :return:
        """
        color = self.pen.color()
        if color ==  Qt.transparent:
            c = self.style().standardPixmap(QStyle.SP_DialogNoButton)
            # mmm make it sexy
            c = c.copy(0, 0, 15, 14).scaled(42, 42)
        else:
            w = max(self.pen.width(), 4) + 1
            c = QPixmap(w, w)
            c.fill(Qt.transparent)
            self.painter.begin(c)
            self.painter.setPen(QPen(Qt.transparent, 0))
            self.painter.setBrush(color)
            self.painter.drawEllipse(0, 0, w, w)
            self.painter.end()

        QApplication.setOverrideCursor(QCursor(c))
        return self.base.enterEvent(event)

    def leaveEvent(self, event):
        """
        Restore cursor to normal.
        :param event:
        :return:
        """
        QApplication.restoreOverrideCursor()
        return self.base.leaveEvent(event)


class ScreenshotContext(object):
    """
    Little thing to handle setting the visuals for taking a screenshot,
    then safely restoring them when finished.
    """
    def __init__(self, obj):
        self.parent = obj.parent()

    def __enter__(self):
        if self.parent:
            self.parent.setWindowOpacity(0)
        QApplication.setOverrideCursor(Qt.CrossCursor)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.parent:
            self.parent.setWindowOpacity(1)
        QApplication.restoreOverrideCursor()


def main(parentWidget=None, isQt=True):
    """
    Convenience function for basic use case.
    Get screenshot with ScreenshotOverlay, pass image to AnnotationWindow,
    and get the final edited image back.
    :parentWidget: optional QObject to use as parent for the windows
    :isQt: bool for whether there is an existing QApp running. Assumed True.
    :return: byte buffer object of image in PNG format
    """
    if not isQt:
        app = QApplication(sys.argv)
    try:
        snap = ScreenshotOverlay(parentWidget)
        with ScreenshotContext(snap):
            res = snap.exec_()
        if res:
            draw = AnnotationWindow(snap.img, parentWidget)
            draw.exec_()
            buf = BytesIO()
            s = draw.final_img.shape
            # png needs it converted into 2D array
            f = numpy.reshape(draw.final_img, (-1, s[1]*s[-1]))
            png.from_array(f, "RGBA;8").save(buf)
            return buf
    except:
        raise
    finally:
        if not isQt:
            app.quit()


if __name__ == '__main__':
    sys.exit(main(isQt=False))
