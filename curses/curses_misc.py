#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" curses_misc.py: Module for various widgets that are used throughout
wicd-curses.
"""

#       Copyright (C) 2008-2009 Andrew Psaltis

#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.

import urwid

from wicd.translations import _
from functools import reduce


# Uses code that is towards the bottom
def error(ui, parent, message):
    """Shows an error dialog (or something that resembles one)"""
    #     /\
    #    /!!\
    #   /____\
    dialog = TextDialog(message, 6, 40, ('important', 'ERROR'))
    return dialog.run(ui, parent)


class SelText(urwid.Text):
    """A selectable text widget. See urwid.Text."""

    def selectable(self):
        """Make widget selectable."""
        return True

    def keypress(self, size, key):
        """Don't handle any keys."""
        return key


class NSelListBox(urwid.ListBox):
    """ Non-selectable ListBox. """
    def selectable(self):
        return False


class DynWrap(urwid.AttrMap):
    """
    Makes an object have mutable selectivity. Attributes will change like
    those in an AttrMap

    w = widget to wrap
    sensitive = current selectable state
    attrs = tuple of (attr_sens, attr_not_sens)
    attrfoc = attributes when in focus, defaults to nothing
    """
    def __init__(self, w, sensitive=True, attrs=('editbx', 'editnfc'), focus_attr='editfc'):
        self._attrs = attrs
        self._sensitive = sensitive

        cur_attr = attrs[0] if sensitive else attrs[1]

        super().__init__(w, cur_attr, focus_attr)

    @property
    def sensitive(self):
        """ Getter for sensitive property. """
        return self._sensitive

    @sensitive.setter
    def sensitive(self, state):
        """ Setter for sensitive property. """
        self.set_attr_map({None: self._attrs[0] if state else self._attrs[1]})
        self._sensitive = state
        self.set_sensitive_recursive(self.original_widget, state)

    @property
    def attrs(self):
        """ Getter for attrs property. """
        return self._attrs

    @attrs.setter
    def attrs(self, attrs):
        """ Setter for attrs property. """
        self._attrs = attrs

    def selectable(self):
        return self._sensitive

    def __getattr__(self, name):
        return getattr(self.original_widget, name)

    def set_sensitive_recursive(self, widget, state):
        """ Set sensitivity recursively for child widgets. """
        if hasattr(widget, 'set_sensitive'):
            widget.set_sensitive(state)
        elif isinstance(widget, urwid.AttrMap):
            self.set_sensitive_recursive(widget.original_widget, state)
        elif isinstance(widget, urwid.WidgetWrap):
            self.set_sensitive_recursive(widget._w, state)
        elif isinstance(widget, urwid.Pile) or isinstance(widget, urwid.ListBox):
            for item in widget.contents:
                self.set_sensitive_recursive(item[0], state)
        # 他の場合でset_sensitiveが定義されていない場合は何もしない
        else:
            pass

    def set_sensitive(self, state):
        """ Enable or disable widget sensitivity based on state. """
        self.sensitive = state
        self.set_sensitive_recursive(self.original_widget, state)



class DynEdit(DynWrap):
    """ Edit DynWrap'ed to the most common specifications. """
    def __init__(self, caption='', edit_text='', sensitive=True,
      attrs=('editbx', 'editnfc'), focus_attr='editfc'):
        caption = ('editcp', caption + ': ')
        edit = urwid.Edit(caption, edit_text)
        super().__init__(edit, sensitive, attrs, focus_attr)


class DynIntEdit(DynWrap):
    """ IntEdit DynWrap'ed to the most common specifications. """
    def __init__(self, caption='', edit_text='', sensitive=True,
      attrs=('editbx', 'editnfc'), focus_attr='editfc'):
        caption = ('editcp', caption + ':')
        edit = urwid.IntEdit(caption, edit_text)
        super().__init__(edit, sensitive, attrs, focus_attr)


class DynRadioButton(DynWrap):
    """ RadioButton DynWrap'ed to the most common specifications. """
    def __init__(self, group, label, state='first True', on_state_change=None,
      user_data=None, sensitive=True, attrs=('body', 'editnfc'),
      focus_attr='body'):
        button = urwid.RadioButton(group, label, state, on_state_change, user_data)
        super().__init__(button, sensitive, attrs, focus_attr)

    def set_sensitive(self, state):
        """ Set sensitivity of RadioButton. """
        self.original_widget.set_state(state)
        self.sensitive = state

class MaskingEditException(Exception):
    """ Custom exception. """
    pass


class MaskingEdit(urwid.Edit):
    """
    mask_mode = one of:
        "always" : everything is a '*' all of the time
        "no_focus" : everything is a '*' only when not in focus
        "off" : everything is always unmasked
    mask_char = the single character that masks all other characters in the
                field
    """
    def __init__(self, caption="", edit_text="", multiline=False, align='left',
      wrap='space', allow_tab=False, edit_pos=None, layout=None,
      mask_mode="always", mask_char='*'):
        self.mask_mode = mask_mode
        if len(mask_char) > 1:
            raise MaskingEditException('Masks of more than one character are not supported!')
        self.mask_char = mask_char
        super().__init__(caption, edit_text, multiline, align, wrap, allow_tab, edit_pos, layout)

    def get_mask_mode(self):
        """ Getter for mask_mode property. """
        return self.mask_mode

    def set_mask_mode(self, mode):
        """ Setter for mask_mode property."""
        self.mask_mode = mode

    def get_masked_text(self):
        """ Get masked out text. """
        return self.mask_char * len(self.get_edit_text())

    def render(self, size, focus=False):
        """
        Render edit widget and return canvas. Include cursor when in focus.
        """
        maxcol, = size
        if self.mask_mode == "off" or (self.mask_mode == 'no_focus' and focus):
            canv = super().render((maxcol,), focus)
            self._invalidate()
            return canv

        self._shift_view_to_cursor = bool(focus)
        text, attr = self.get_text()
        text = text[:len(self.caption)] + self.get_masked_text()
        trans = self.get_line_translation(maxcol, (text, attr))
        canv = urwid.canvas.apply_text_layout(text, attr, trans, maxcol)

        if focus:
            canv = urwid.CompositeCanvas(canv)
            canv.cursor = self.get_cursor_coords((maxcol,))

        return canv


class TabColumns(urwid.WidgetWrap):
    """
    Tabbed interface, mostly for use in the Preferences Dialog

    titles_dict = dictionary of tab_contents (a SelText) : tab_widget (box)
    attr = normal attributes
    attrsel = attribute when active
    """
    def __init__(self, tab_str, tab_wid, title, bottom_part=None,
      attr=('body', 'focus'), attrsel='tab active', attrtitle='header'):
        column_list = []
        for w in tab_str:
            # 修正部分: wがAttrMapである場合、元のウィジェットからget_textを呼び出す
            if isinstance(w, urwid.AttrMap):
                text, trash = w.base_widget.get_text()
            else:
                text, trash = w.get_text()
            column_list.append(('fixed', len(text), w))
        column_list.append(urwid.Text((attrtitle, title), align='right'))

        self.tab_map = dict(zip(tab_str, tab_wid))
        self.active_tab = tab_str[0]
        self.columns = urwid.Columns(column_list, dividechars=1)
        self.gen_pile(tab_wid[0], True)
        self.frame = urwid.Frame(self.pile)
        super().__init__(self.frame)


    def gen_pile(self, lbox, firstrun=False):
        """ Make the pile in the middle. """
        self.pile = urwid.Pile([
            ('fixed', 1, urwid.Filler(self.columns, 'top')),
            urwid.Filler(lbox, 'top', height=('relative', 99)),
        ])
        if not firstrun:
            self.frame.set_body(self.pile)
            self._w = self.frame
            self._invalidate()

    def selectable(self):
        """ Return whether the widget is selectable. """
        return True

    def keypress(self, size, key):
        """ Handle keypresses. """
        if key == "page up" or key == "page down":
            self._w.get_body().set_focus(0)
            newK = 'left' if key == "page up" else 'right'
            self.keypress(size, newK)
            self._w.get_body().set_focus(1)
        else:
            key = self._w.keypress(size, key)
            wid = self.pile.get_focus().get_body()
            if wid == self.columns:
                self.active_tab.set_attr_map({None: 'body'})
                self.columns.get_focus().set_attr_map({None: 'tab active'})
                self.active_tab = self.columns.get_focus()
                self.gen_pile(self.tab_map[self.active_tab])

        return key

    def mouse_event(self, size, event, button, x, y, focus):
        """ Handle mouse events. """
        wid = self.pile.get_focus().get_body()
        if wid == self.columns:
            self.active_tab.set_attr_map({None: 'body'})

        self._w.mouse_event(size, event, button, x, y, focus)
        if wid == self.columns:
            self.active_tab.set_attr_map({None: 'body'})
            self.columns.get_focus().set_attr_map({None: 'tab active'})
            self.active_tab = self.columns.get_focus()
            self.gen_pile(self.tab_map[self.active_tab])


class ComboBoxException(Exception):
    """ Custom exception. """
    pass


class ComboBox(urwid.WidgetWrap):
    """A ComboBox of text objects"""
    class ComboSpace(urwid.WidgetWrap):
        """The actual menu-like space that comes down from the ComboBox"""
        def __init__(self, l, body, ui, show_first, pos=(0, 0), attr=('body', 'focus')):
            """
            body      : parent widget
            l         : stuff to include in the combobox
            ui        : the screen
            show_first: index of the element in the list to pick first
            pos       : a tuple of (row,col) where to put the list
            attr      : a tuple of (attr_no_focus,attr_focus)
            """

            height = len(l)
            width = max(len(entry) for entry in l)
            content = [urwid.AttrMap(SelText(w), attr[0], attr[1]) for w in l]
            self._listbox = urwid.ListBox(content)
            if show_first is None or show_first >= len(l) or show_first < 0:
                show_first = 0
            self._listbox.set_focus(show_first)
            self.overlay = urwid.Overlay(self._listbox, body, ('fixed left', pos[0]), width + 2, ('fixed top', pos[1]), height)
            super().__init__(self.overlay)

        def show(self, ui, display):
            """ Show widget. """
            dim = ui.get_cols_rows()
            keys = True

            while True:
                if keys:
                    ui.draw_screen(dim, self.render(dim, True))

                keys = ui.get_input()

                if "window resize" in keys:
                    dim = ui.get_cols_rows()
                if "esc" in keys:
                    return None
                if "enter" in keys:
                    (wid, pos) = self._listbox.get_focus()
                    (text, attr) = wid.base_widget.get_text()
                    return text

                for k in keys:
                    self._w.keypress(dim, k)

    def __init__(self, label='', l=None, attrs=('body', 'editnfc'), focus_attr='focus', use_enter=True, focus=0, callback=None, user_args=None, overlay=None):
        """
        label     : bit of text that preceeds the combobox.  If it is "", then ignore it
        l         : stuff to include in the combobox
        body      : parent widget
        ui        : the screen
        row       : where this object is to be found onscreen
        focus     : index of the element in the list to pick first
        callback  : function that takes (combobox,sel_index,user_args=None)
        user_args : user_args in the callback
        """

        self.DOWN_ARROW = '    vvv'
        self.label = urwid.Text(label)
        self.attrs = attrs
        self.focus_attr = focus_attr
        self.list = l if l is not None else []
        self.overlay = overlay  # Use the passed overlay if available
        s, trash = self.label.get_text()
        self.cbox = DynWrap(SelText(self.DOWN_ARROW), attrs=attrs, focus_attr=focus_attr)
        if label != '':
            w = urwid.Columns([('fixed', len(s), self.label), self.cbox], dividechars=1)
        else:
            w = urwid.Columns([self.cbox])
        super().__init__(w)
        self.use_enter = use_enter
#        self.focus = focus
        self.callback = callback
        self.user_args = user_args

    def build_overlay(self, ui, body):
        """ Build the overlay for the combo box. """
        if not self.overlay:
            self.overlay = self.ComboSpace(self.list, body, ui, self.focus, pos=(0, 0))

    def set_list(self, l):
        """ Populate widget list. """
        self.list = l

    def set_focus(self, index):
        """ Set widget focus. """
        if not self.list or index < 0 or index >= len(self.list):  # リストが空、またはインデックスが範囲外の場合、何もしない
            return

        if urwid.__version__ < "1.1.0":
            self.focus = index
        else:
            try:
                self._w.focus_position = index
            except IndexError:
                pass

        try:
            self.cbox.original_widget.set_text(self.list[index] + self.DOWN_ARROW)
        except AttributeError:
            self.cbox.base_widget = SelText(self.list[index] + self.DOWN_ARROW)
        if self.overlay:
            self.overlay._listbox.set_focus(index)

    def rebuild_combobox(self):
        """ Rebuild combobox. """
        self.build_combobox(self.parent, self.ui, self.row)

    def build_combobox(self, parent, ui, row):
        """ Build combobox. """
        s, trash = self.label.get_text()

        if urwid.__version__ < "1.1.0":
            index = self.focus
        else:
            index = self._w.focus_position

        self.cbox = DynWrap(SelText(self.list[index] + self.DOWN_ARROW), attrs=self.attrs, focus_attr=self.focus_attr)
        if s != '':
            w = urwid.Columns([('fixed', len(s), self.label), self.cbox], dividechars=1)
            self.overlay = self.ComboSpace(self.list, parent, ui, index, pos=(len(s) + 1, row))
        else:
            w = urwid.Columns([self.cbox])
            self.overlay = self.ComboSpace(self.list, parent, ui, index, pos=(0, row))

        self._w = w
        self._invalidate()
        self.parent = parent
        self.ui = ui
        self.row = row

    def keypress(self, size, key):
        """ Handle keypresses. """
        activate = key == ' '
        if self.use_enter:
            activate = activate or key == 'enter'
        if activate:
            if self.overlay is None:
                raise ComboBoxException('ComboBox must be built before use!')
            retval = self.overlay.show(self.ui, self.parent)
            if retval is not None:
                self.set_focus(self.list.index(retval))
                if self.callback is not None:
                    self.callback(self, self.overlay._listbox.get_focus()[1], self.user_args)
        return self._w.keypress(size, key)

    def selectable(self):
        """ Return whether the widget is selectable. """
        return self.cbox.selectable()

    def get_focus(self):
        """ Return widget focus. """
        if self.overlay:
            return self.overlay._listbox.get_focus()
        else:
            if urwid.__version__ < "1.1.0":
                return None, self.focus
            else:
                return None, self._w.focus_position

    def get_sensitive(self):
        """ Return widget sensitivity. """
        return self.cbox.sensitive

    def set_sensitive(self, state):
        """ Set widget sensitivity. """
        self.cbox.sensitive = state


class DialogExit(Exception):
    """ Custom exception. """
    pass


class Dialog2(urwid.WidgetWrap):
    """ Base class for other dialogs. """
    def __init__(self, text, height, width, body=None):
        self.buttons = None

        self.width = int(width)
        if width <= 0:
            self.width = ('relative', 80)
        self.height = int(height)
        if height <= 0:
            self.height = ('relative', 80)

        self.body = body
        if body is None:
            body = urwid.Filler(urwid.Divider(), 'top')

        self.frame = urwid.Frame(body, focus_part='footer')
        if text is not None:
            self.frame.header = urwid.Pile([urwid.Text(text, align='right'), urwid.Divider()])
        w = self.frame
        self.view = w
        super().__init__(w)

    def add_buttons(self, buttons):
        """ Add buttons. """
        l = []
        maxlen = 0
        for name, exitcode in buttons:
            b = urwid.Button(name, self.button_press)
            b.exitcode = exitcode
            b = urwid.AttrMap(b, 'body', 'focus')
            l.append(b)
            maxlen = max(len(name), maxlen)
        maxlen += 4
        self.buttons = urwid.GridFlow(l, maxlen, 3, 1, 'center')
        self.frame.footer = urwid.Pile([urwid.Divider(), self.buttons], focus_item=1)

    def button_press(self, button):
        """ Handle button press. """
        raise DialogExit(button.exitcode)

    def run(self, ui, parent):
        """ Run the UI. """
        ui.set_mouse_tracking()
        size = ui.get_cols_rows()
        overlay = urwid.Overlay(urwid.LineBox(self.view), parent, 'center', self.width, 'middle', self.height)
        try:
            while True:
                canvas = overlay.render(size, focus=True)
                ui.draw_screen(size, canvas)
                keys = ui.get_input()
                for k in keys:
                    if k == 'window resize':
                        size = ui.get_cols_rows()
                    k = self.view.keypress(size, k)
                    if k == 'esc':
                        raise DialogExit(-1)
                    if k:
                        self.unhandled_key(size, k)
        except DialogExit as e:
            return self.on_exit(e.args[0])

    def on_exit(self, exitcode):
        """ Handle dialog exit. """
        return exitcode, ""

    def unhandled_key(self, size, key):
        """ Handle keypresses. """
        pass


class TextDialog(Dialog2):
    """ Simple dialog with text and "OK" button. """
    def __init__(self, text, height, width, header=None, align='left', buttons=(_('OK'), 1)):
        l = [urwid.Text(text)]
        body = urwid.ListBox(l)
        body = urwid.AttrMap(body, 'body')

        Dialog2.__init__(self, header, height + 2, width + 2, body)
        if type(buttons) == list:
            self.add_buttons(buttons)
        else:
            self.add_buttons([buttons])

    def unhandled_key(self, size, k):
        """ Handle keys. """
        if k in ('up', 'page up', 'down', 'page down'):
            self.frame.set_focus('body')
            self.view.keypress(size, k)
            self.frame.set_focus('footer')


class InputDialog(Dialog2):
    """ Simple dialog with text and entry. """
    def __init__(self, text, height, width, ok_name=_('OK'), edit_text=''):
        self.edit = urwid.Edit(wrap='clip', edit_text=edit_text)
        body = urwid.ListBox([self.edit])
        body = urwid.AttrMap(body, 'editbx', 'editfc')

        Dialog2.__init__(self, text, height, width, body)

        self.frame.set_focus('body')
        self.add_buttons([(ok_name, 0), (_('Cancel'), -1)])

    def unhandled_key(self, size, k):
        """ Handle keys. """
        if k in ('up', 'page up'):
            self.frame.set_focus('body')
        if k in ('down', 'page down'):
            self.frame.set_focus('footer')
        if k == 'enter':
            self.frame.set_focus('footer')
            self.view.keypress(size, k)

    def on_exit(self, exitcode):
        """ Handle dialog exit. """
        return exitcode, self.edit.get_edit_text()


class ClickCols(urwid.WidgetWrap):
    """ Clickable menubar. """
    def __init__(self, items, callback=None, args=None):
        cols = urwid.Columns(items)
        super().__init__(cols)
        self.callback = callback
        self.args = args

    def mouse_event(self, size, event, button, x, y, focus):
        """ Handle mouse events. """
        if event == "mouse press":
            self.callback([self.args])


class OptCols(urwid.WidgetWrap):
    """ Htop-style menubar on the bottom of the screen. """
    def __init__(self, tuples, handler, attrs=('body', 'infobar'), debug=False):
        textList = []
        self.callbacks = []
        for cmd in tuples:
            key = reduce(lambda s, tuple: s.replace(tuple[0], tuple[1]), [
                ('ctrl ', 'Ctrl+'), ('meta ', 'Alt+'),
                ('left', '<-'), ('right', '->'),
                ('page up', 'Page Up'), ('page down', 'Page Down'),
                ('esc', 'ESC'), ('enter', 'Enter'), ('s', 'S')], cmd[0])

            callback = self.debugClick if debug else handler
            args = cmd[1] if debug else cmd[0]
            col = ClickCols([('fixed', len(key) + 1, urwid.Text((attrs[0], key + ':'))), urwid.AttrMap(urwid.Text(cmd[1]), attrs[1])], callback, args)
            textList.append(col)

        if debug:
            self.debug = urwid.Text("DEBUG_MODE")
            textList.append(('fixed', 10, self.debug))

        cols = urwid.Columns(textList)

        super().__init__(cols)

    def debugClick(self, args):
        """ Debug clicks. """
        self.debug.set_text(args)

    def mouse_event(self, size, event, button, x, y, focus):
        """ Handle mouse events. """
        return self._w.mouse_event(size, event, button, x, y, focus)
