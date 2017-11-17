# -*- coding: utf-8 -*-

import re

from aqt import mw
from aqt.utils import showInfo
from aqt.addcards import AddCards
from aqt.browser import Browser
from aqt.editcurrent import EditCurrent
from aqt.utils import tooltip
from anki.hooks import addHook, wrap
from aqt.editor import Editor
from aqt.qt import *

# global variables
genuine_answer_arr = []
genuine_hint_arr = []
pseudo_answer_arr = []
pseudo_hint_arr = []
current_cloze_field_number = 0

hidden_block_content_arr = []

# constants
MODEL_NAME = "0 Enhanced Cloze"
CONTENT_FIELD_NAME = "# Content"
VALID_CLOZES_FIELD_NAME = "Valid Clozes"


def generate_enhanced_cloze(note):
    # cloze_id like c1, cloze_number like 1

    # Some specific pre-processing of content
    src_field_name = CONTENT_FIELD_NAME
    src_field_content = note[src_field_name]
    src_field_content = setup_url(src_field_content)
    src_field_content = setup_quote(src_field_content)
    global hidden_block_content_arr
    del hidden_block_content_arr[:]
    src_field_content = setup_hidden_block(src_field_content)

    # Get ids of valid clozes
    cloze_start_regex = r"\{\{c\d+::"
    cloze_start_matches = re.findall(cloze_start_regex, src_field_content)

    # if no clozes found, empty Cloze1~Cloze99 and fill in Cloze99
    if not cloze_start_matches:
        for i_cloze_field_number in range(1, 20 + 1):
            dest_field_name = "Cloze%s" % i_cloze_field_number
            note[dest_field_name] = ""

        note[VALID_CLOZES_FIELD_NAME] = ""

        note["Cloze99"] = src_field_content + \
            '<div style="display:none">{{c99::@@}}</div>' + \
            '<div id="card-cloze-id" style="display:none">c99</div>'
        return True
    else:
        note["Cloze99"] = ""

        valid_cloze_numbers = sorted(
            [int(re.sub(r"\D", "", x)) for x in set(cloze_start_matches)])
        note[VALID_CLOZES_FIELD_NAME] = str(valid_cloze_numbers)

        # Fill in content in valid cloze fields and empty content in invalid fields
        global current_cloze_field_number
        for current_cloze_field_number in range(1, 20 + 1):

            dest_field_name = "Cloze%s" % current_cloze_field_number
            dest_field_content = ""

            if not (current_cloze_field_number in valid_cloze_numbers):
                dest_field_content = ""
            else:
                # Initialize the lists
                global genuine_answer_arr
                global genuine_hint_arr
                global pseudo_answer_arr
                global pseudo_hint_arr

                del genuine_answer_arr[:]
                del genuine_hint_arr[:]
                del pseudo_answer_arr[:]
                del pseudo_hint_arr[:]

                dest_field_content = src_field_content

                cloze_regex = r"\{\{c\d+::[\s\S]*?\}\}"
                dest_field_content = re.sub(
                    cloze_regex, process_cloze, dest_field_content)

                # Store answer and hint (gunuine or pseudo) in html of every valid cloze fields
                for index, item in enumerate(genuine_answer_arr):
                    dest_field_content += '<pre style="display:none"><div id="genuine-answer-%s">%s</div></pre>' % (
                        index, item)
                for index, item in enumerate(genuine_hint_arr):
                    dest_field_content += '<pre style="display:none"><div id="genuine-hint-%s">%s</div></pre>' % (
                        index, item)
                for index, item in enumerate(pseudo_answer_arr):
                    dest_field_content += '<pre style="display:none"><div id="pseudo-answer-%s">%s</div></pre>' % (
                        index, item)
                for index, item in enumerate(pseudo_hint_arr):
                    dest_field_content += '<pre style="display:none"><div id="pseudo-hint-%s">%s</div></pre>' % (
                        index, item)

                for index, item in enumerate(hidden_block_content_arr):
                    dest_field_content += '<pre style="display:none"><div id="hidden-block-%s">%s</div></pre>' % (
                        index, item)

                # Anki don't recognize multi-line clozes as valid clozes ,
                # so just use a hidden single line cloze to pass the test
                dest_field_content += '<div style="display:none">{{c%s::@@}}</div>' % current_cloze_field_number
                dest_field_content += '<div id="card-cloze-id" style="display:none">c%s</div>' % str(
                    current_cloze_field_number)

            note[dest_field_name] = dest_field_content
        return True


def check_model(model):
    return model["name"] == MODEL_NAME


def setup_url(html_text):
    return re.sub(r"((https?|ftp|file)://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|])", r'<a href="\1">\1</a>', html_text)


def setup_quote(html_text):
    return re.sub(r"('''[\s\S]*?(?:</div>?)\s*?)(<div>[\s\S]*?</div>)(\s*?<div>''')", r'\1<div class="quote">\2</div>\3', html_text)


def setup_hidden_block(html_text):
    return re.sub(r"(--hide on--[\s\S]*?<div>)([\s\S]*?)(</div>\s*?<div>+--hide off--)", process_hidden_block_content, html_text)


def process_hidden_block_content(matchObj):
    global hidden_block_content_arr
    hidden_block_content = str(matchObj.group(2))
    hidden_block_content_arr.append(hidden_block_content)
    index_in_arr = len(hidden_block_content_arr) - 1
    wrapped_hidden_block_content = r'<span class="hidden-block" index="%s">%s</span>' % (
        str(index_in_arr), hidden_block_content)
    return str(matchObj.group(1)) + wrapped_hidden_block_content + str(matchObj.group(3))


def process_cloze(matchObj):

    cloze_string = str(matchObj.group())  # like: {{c1::aa[::bbb]}}
    index_of_answer = cloze_string.find("::") + 2
    index_of_hint = cloze_string.rfind("::") + 2
    cloze_id = cloze_string[2: index_of_answer - 2]  # like: c1
    cloze_length = len(cloze_string)

    answer = ""
    hint = ""
    if (index_of_answer == index_of_hint):
        answer = cloze_string[index_of_answer: cloze_length - 2]
        hint = ""
    else:
        answer = cloze_string[index_of_answer: index_of_hint - 2]
        hint = cloze_string[index_of_hint: cloze_length - 2]

    global current_cloze_field_number
    if (cloze_id != 'c' + str(current_cloze_field_number)):
        # Process pseudo-cloze
        global pseudo_answer_arr
        global pseudo_hint_arr
        pseudo_answer_arr.append(answer)
        pseudo_hint_arr.append(hint)
        index_in_arr = len(pseudo_answer_arr) - 1
        new_html = '<span class="pseudo-cloze" index="_index_" show-state="hint" cloze-id="_cloze-id_">_content_</span>'
        new_html = new_html.replace('_index_', str(index_in_arr)).replace(
            '_cloze-id_', str(cloze_id)).replace('_content_', cloze_string.replace("{", '[').replace("}", "]"))
        return new_html
    else:
        # Process genuine-cloze
        global genuine_answer_arr
        global genuine_hint_arr
        genuine_answer_arr.append(answer)
        genuine_hint_arr.append(hint)
        index_in_arr = len(genuine_answer_arr) - 1
        new_html = '<span class="genuine-cloze" index="_index_" show-state="hint" cloze-id="_cloze-id_">_content_</span>'
        new_html = new_html.replace('_index_', str(index_in_arr)).replace(
            '_cloze-id_', str(cloze_id)).replace('_content_', str(cloze_string))
        return new_html


def on_add_cards(self, _old):
    note = self.editor.note
    if not note or not check_model(note.model()):
        return _old(self)
    generate_enhanced_cloze(note)
    ret = _old(self)
    # tooltip('Enhanced Cloze Added')
    return ret


def on_edit_current(self, _old):
    note = self.editor.note
    if not note or not check_model(note.model()):
        return _old(self)
    generate_enhanced_cloze(note)
    ret = _old(self)
    # tooltip('Enhanced Cloze Updated')
    return ret


def update_all_enhanced_clozes_in_browser(self, evt=None):
    browser = self
    mw = browser.mw

    mw.checkpoint("Update Enhanced Clozes")
    mw.progress.start()
    browser.model.beginReset()

    update_all_enhanced_cloze(self)

    browser.model.endReset()
    mw.requireReset()
    mw.progress.finish()
    mw.reset()
    # tooltip('Enhanced Clozes Updated.')


def update_all_enhanced_cloze(self):
    mw = self.mw
    nids = mw.col.findNotes("tag:*")
    for nid in nids:
        note = mw.col.getNote(nid)
        if not check_model(note.model()):
            break
        generate_enhanced_cloze(note)
        note.flush()
    # tooltip('Enhanced Clozes Updated.')


def setup_menu(self):
    browser = self
    menu = browser.form.menuEdit
    menu.addSeparator()
    a = menu.addAction('Update Enhanced Clozes')
    a.setShortcut(QKeySequence("Ctrl+Shift+C"))
    a.triggered.connect(lambda _, b=browser: update_all_enhanced_clozes_in_browser(b))

def on_save_now(self, callback=None):
    update_all_enhanced_cloze(self)


AddCards.addCards = wrap(AddCards.addCards, on_add_cards, "around")

EditCurrent.onSave = wrap(EditCurrent.onSave, on_edit_current, "around")
# Browser.closeEvent = wrap(
#     Browser.closeEvent, update_all_enhanced_clozes_in_browser, "before")

Editor.saveNow = wrap(Editor.saveNow, on_save_now, "before")

addHook("browser.setupMenus", setup_menu)  # see Batch Edit add-on

# addHook('editFocusLost', onFocusLost)
