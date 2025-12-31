"""
Mobject representing highlighted source code listings (ManimGL).
"""

from __future__ import annotations

__all__ = ["Code"]

import re
from pathlib import Path
from typing import Any, Literal

from bs4 import BeautifulSoup, Tag
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers import (
    get_lexer_by_name,
    guess_lexer,
    guess_lexer_for_filename,
)
from pygments.styles import get_all_styles

from manimlib import *
from colour import Color




def preserve_spaces(s: str) -> str:
    """ManimGL does not render normal spaces correctly."""
    return s.replace(" ", "\u00A0")


class Code(VMobject):
    """A highlighted source code listing for ManimGL."""

    _styles_list_cache = None

    default_background_config = {
        "buff": 0.7,
        "fill_color": Color("#222222"),
        "stroke_color": WHITE,
        "stroke_width": 1,
        "fill_opacity": 1,
    }

    default_text_config = {
        # "font": "Monospace",
    }

    def __init__(
        self,
        code_file=None,
        code_string=None,
        language=None,
        formatter_style="vim",
        tab_width=4,
        add_line_numbers=True,
        line_numbers_from=1,
        background: Literal["rectangle", "window"] = "rectangle",
        border_radius: float =.4,
        tabs_opacity: float =.2,
        background_config=None,
        text_config=None,
    ):
        super().__init__()

        # ---------------- Load code ----------------
        if code_file:
            code_file = Path(code_file)
            code_string = code_file.read_text(encoding="utf-8")
            lexer = guess_lexer_for_filename(code_file.name, code_string)
        elif code_string:
            lexer = get_lexer_by_name(language) if language else guess_lexer(code_string)
        else:
            raise ValueError("Either code_file or code_string must be specified.")

        code_string = code_string.expandtabs(tab_width).replace(' '*tab_width,"\u00B7"*tab_width)
        
        code_lines_=code_string.split('\n')
        # ---------------- Pygments ----------------
        formatter = HtmlFormatter(
            style=formatter_style,
            noclasses=True,
            cssclasses="",
            )
        
        soup = BeautifulSoup(
            highlight(code_string, lexer, formatter),
            "html.parser"
            )
        
        pre = soup.find("pre")
        self._code_html = pre
        assert isinstance(pre, Tag)

        color_ranges = []
        current_line_color_ranges = []
        current_line_char_index = 0

        def num_spaces_before(line_ind,start_ind):
            if start_ind==0:
                return 0
            line=code_lines_[line_ind][:start_ind]
            return line.count(' ')
        

        i=0
        for child in self._code_html.children:
            if child.name == "span":
                try:
                    child_style = child["style"]
                    match_ = re.match(
                        r"color: (#[A-Fa-f0-9]{6}|#[A-Fa-f0-9]{3})", child_style
                    )
                    color = None if match_ is None else match_.group(1)
                except KeyError:
                    color = None
                n=num_spaces_before(i,current_line_char_index)
                current_line_color_ranges.append(
                    (
                        current_line_char_index,
                        current_line_char_index + len(child.text),
                        color,
                        n
                    )
                )
                
                current_line_char_index += len(child.text)
            else:
                for char in child.text:
                    if char == "\n":
                        i+=1
                        color_ranges.append(current_line_color_ranges)
                        current_line_color_ranges = []
                        current_line_char_index = 0
                    else:
                        current_line_char_index += 1

        color_ranges.append(current_line_color_ranges)
        code_lines = self._code_html.get_text().removesuffix("\n").split("\n")
        
        
        paragraph_config=self.default_text_config
        # ---------------- Build text ----------------
        if paragraph_config is None:
            paragraph_config = {}
        base_paragraph_config = self.default_text_config.copy()
        base_paragraph_config.update(paragraph_config)

        from Paragraph import Paragraph

        self.code_lines = Paragraph(
            *code_lines,
            show_spaces=True,
            space_dot_opacity=tabs_opacity,
            background_color=self.default_background_config['fill_color'],
            **base_paragraph_config,
        )
        i=0
        for line, color_range in zip(self.code_lines, color_ranges):
            for start, end, color,n in color_range:
                line[0][start-n:end-n].set_color(color)
            i+=1

        if add_line_numbers:
            base_paragraph_config.update({"alignment": "right"})
            self.line_numbers = VGroup(
                *[
                    Text(str(i),**base_paragraph_config,weight='bold').next_to(self.code_lines[i-1], direction=LEFT*1.5).scale(.8)
                    for i in range(
                        line_numbers_from, line_numbers_from + len(self.code_lines)
                    )
                ],
            )
            # self.line_numbers.next_to(self.code_lines, direction=LEFT).align_to(
            #     self.code_lines, UP
            # )
            self.add(self.line_numbers)

        for line in self.code_lines:
            line.submobjects = [c for c in line if not isinstance(c, Dot)]
        self.add(self.code_lines)



        # ---------------- Background ----------------
        if background_config is None:
            background_config = {}
        bg_conf = self.default_background_config.copy()
        bg_conf.update(background_config)

        if background == "rectangle":
            bg = SurroundingRectangle(self, **bg_conf)
        elif background == "window":
            buttons = VGroup(
                Dot(radius=0.17, fill_color=Color(c), stroke_width=0)
                for c in ["#ff5f56", "#ffbd2e", "#27c93f"]
            ).arrange(RIGHT, buff=0.1)

            buttons.next_to(self, UP, buff=0.45).align_to(self, LEFT)
            bg = SurroundingRectangle(VGroup(self, buttons), **bg_conf)
            bg.add(buttons)
        else:
            raise ValueError(f"Unknown background type: {background}")
        bg.round_corners(border_radius)
        self.add_to_back(bg)
        self.scale(.45)
        self.center()

        self.highlighted_lines=set()



    def highlight_line(self,line):

        self.highlighted_lines.add(line-1)

        to_fade=VGroup()
        for i in range(len(self.code_lines)):
            if i in self.highlighted_lines:
                self.code_lines[i].set_opacity(1)
                self.line_numbers[i].set_opacity(1)
            else:
                to_fade.add(self.code_lines[i],self.line_numbers[i])
        to_fade.set_opacity(.2)
        for i in range(len(self.code_lines)):
            if '\u00B7' in self.code_lines[i][0].get_string():
                self.code_lines[i][0].set_color_by_text('\u00B7',self.default_background_config['fill_color'])
        
    def remove_highlighting_from_line(self,line):
        self.highlighted_lines.remove(line-1)
        self.code_lines[line-1].set_opacity(.2)
        self.line_numbers[line-1].set_opacity(.2)




    @classmethod
    def get_styles_list(cls):
        if cls._styles_list_cache is None:
            cls._styles_list_cache = list(get_all_styles())
        return cls._styles_list_cache


import os,sys
sys.path.append(os.curdir)

class Test(Scene):
    def construct(self):
        code=Code(
            'test.py',
            formatter_style='vim',
            background="window",
            tabs_opacity=0,
            tab_width=3
        )
        code.highlight_line(1)
        code.highlight_line(2)
        code.remove_highlighting_from_line(2)
        code.highlight_line(3)
        code.highlight_line(9)
        code.highlight_line(12)
        self.add(code)
        self.wait(2)