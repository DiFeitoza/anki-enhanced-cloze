# -*- coding: utf-8 -*-

import re

from anki.hooks import addHook
from aqt import mw
from aqt.utils import showInfo


def onFocusLost(flag, n, fidx):

    TEMPLATE_NAME = "0 Cloze MULTIPLE"
    CONTENT_FIELD_NAME = "# Content"
    VALID_CLOZES_FIELD_NAME = "Valid Clozes"

    # Check template
    if TEMPLATE_NAME != n.model()['name']:
        return flag

    # ensure relevant lost-focus source field
    src_field_name = None
    src_field_index = None

    for index, name in enumerate(mw.col.models.fieldNames(n.model())):
        if CONTENT_FIELD_NAME == name:
            src_field_name = name
            src_field_index = index
            break
    if not src_field_name:
        return flag
    if src_field_index != fidx:
        return flag

    src_field_content = n[src_field_name]

    # get valid cloze ids
    cloze_start_regex = r"\{\{c\d+::"
    cloze_start_pattern = re.compile(cloze_start_regex)
    cloze_start_matches = re.findall(cloze_start_pattern, src_field_content)

    # deal with no cloze issue
    if not cloze_start_matches:
        for iLoop in range(20, 0, -1):
            dest_field_name = "Cloze%s" % iLoop
            dest_field_content = ""
            n[dest_field_name] = dest_field_content
        n["Cloze99"] = src_field_content + \
            r'<div style="display:none">{{c99::$$}}</div>' + \
            r'<div id="card-cloze-id" style="display:none">c99</div>'
        return True
    else:
        n["Cloze99"]=""

    cloze_start_matches_unique = set(cloze_start_matches)
    valid_cloze_ids = sorted(
        [int(re.sub(r"\D", "", x)) for x in cloze_start_matches_unique])
    n[VALID_CLOZES_FIELD_NAME] = str(valid_cloze_ids)

    # fill in content in valid cloze fields and empty content in invalid fields
    for iLoop in range(20, 0, -1):
        dest_field_name = "Cloze%s" % iLoop
        dest_field_content = None

        if not (iLoop in valid_cloze_ids):
            dest_field_content = ""
        else:
            dest_field_content = src_field_content

            # change all {{c*::}} to [[c*::]]
            cloze_regex = r"(\{\{)(c\d+::([\s\S]*?))(\}\})"
            cloze_pattern = re.compile(cloze_regex)
            dest_field_content = re.sub(
                cloze_pattern, r"[[\2]]", dest_field_content)

            # change current field back to {{c*::)}}
            cloze_regex = r"(\[\[)(c%s::([\s\S]*?))(\]\])" % iLoop
            cloze_pattern = re.compile(cloze_regex)
            dest_field_content = re.sub(
                cloze_pattern, r"{{\2}}", dest_field_content)

            # workaround for multiple line cloze not being recognized as cloze
            dest_field_content += r'<div style="display:none">{{c%s::$$}}</div>' % iLoop
            dest_field_content += r'<div id="card-cloze-id" style="display:none">c%s</div>' % str(
                iLoop)

        n[dest_field_name] = dest_field_content

    return True


addHook('editFocusLost', onFocusLost)
# iLoop = 20
# while iLoop > 0:
#     cloze_regex = r"\{\{c%s\:\:([\s\S]*?)(\:\:([\s\S]*?))?\}\}" % iLoop
#     cloze_pattern = re.compile(cloze_regex)
#     cloze_match = cloze_pattern.search(src_field_content)
#     if cloze_match:
#         cloze_index_max = iLoop
#         break
#     iLoop -= 1

# iLoop = 20
# while iLoop > cloze_index_max:
#     dest_field_name = r'Cloze%s (MLT)' % iLoop
#     dest_field_content = str('')
#     n[dest_field_name] = dest_field_content
#     iLoop -= 1

# iLoop = cloze_index_max
# while iLoop > 0:
#     dest_field_name = r'Cloze%s (MLT)' % iLoop
#     dest_field_content = src_field_content

#     cloze_regex = r"(\{\{)(c\d+\:\:([\s\S]*?)(\:\:([\s\S]*?))?)(\}\})"
#     cloze_pattern = re.compile(cloze_regex)
#     dest_field_content = re.sub(
#         cloze_pattern, r"[[\2]]", dest_field_content)

#     cloze_regex = r"(\[\[)(c%s\:\:([\s\S]*?)(\:\:([\s\S]*?))?)(\]\])" % iLoop
#     cloze_pattern = re.compile(cloze_regex)
#     dest_field_content = re.sub(
#         cloze_pattern, r"{{\2}}", dest_field_content)

# jLoop = cloze_index_max
# while jLoop > 0:
#     if not jLoop == iLoop:
#         cloze_regex = r"(\{\{)(c%s\:\:([\s\S]*?)(\:\:([\s\S]*?))?)(\}\})" % jLoop
#         cloze_pattern = re.compile(cloze_regex)
#         dest_field_content = re.sub(
#             cloze_pattern, r"[[\2]]", dest_field_content)
#     jLoop -= 1

# n[dest_field_name] = dest_field_content
# iLoop -= 1
# return True
