from manimlib import *

class Paragraph(VGroup):
   
    def __init__(
        self,
        *text: str,
        line_spacing: float = -1,
        alignment: str | None = 'left',
        show_spaces: bool = True,
        space_dot_opacity: float = 0,
        **kwargs,
    ):
        self.show_spaces=show_spaces
        self.space_dot_opacity=space_dot_opacity
        self.line_spacing = line_spacing
        self.alignment = alignment
        self.consider_spaces_as_chars = kwargs.get("disable_ligatures", True)
        super().__init__()

        lines_str = "\n".join(list(text))
        # self.lines_text = Text(lines_str, line_spacing=line_spacing, **kwargs)
        self.lines_text = Text(lines_str, **kwargs)
        lines_str_list = lines_str.split("\n")
        self.chars = self._gen_chars(lines_str_list)

        self.lines = [list(self.chars), [self.alignment] * len(self.chars)]
        self.lines_initial_positions = [line.get_center() for line in self.lines[0]]
        self.add(*self.lines[0])
        self.move_to(np.array([0, 0, 0]))
        self.chars.arrange(DOWN)
        if self.alignment:
            self._set_all_lines_alignments(self.alignment)

    def _gen_chars(self, lines_str_list: list) -> VGroup:
        """Function to convert a list of plain strings to a VGroup of VGroups of chars.

        Parameters
        ----------
        lines_str_list
            List of plain text strings.

        Returns
        -------
        :class:`~.VGroup`
            The generated 2d-VGroup of chars.
        """
        char_index_counter = 0
        chars = self.get_group_class()()
        for line_no in range(len(lines_str_list)):
            line_str = lines_str_list[line_no]
            # Count all the characters in line_str
            # Spaces may or may not count as characters
            if self.consider_spaces_as_chars:
                char_count = len(line_str)
            else:
                char_count = 0
                for char in line_str:
                    if not char.isspace():
                        char_count += 1

            chars.add(self.get_group_class()())
            # print(self.lines_text.get_string())
            
            # chars[line_no].add(
            #     *[Text(r) for r in 
            #         [*self.lines_text.get_string()[
            #         char_index_counter : char_index_counter + char_count
            #     ]]]
            # )

            if self.show_spaces:
                s=''.join([*self.lines_text.get_string()[
                        char_index_counter : char_index_counter + char_count
                    ]])
                import re
                s = re.sub(r'^( {2,})', lambda m: m.group(1).replace(' ', '\u00B7'), s)
                t=Text(s)

                for i in range(len(s)) :
                    if s[i]=='\u00B7':
                        t[i].set_opacity(self.space_dot_opacity)
            else:   
                t=Text(''.join([*self.lines_text.get_string()[
                        char_index_counter : char_index_counter + char_count
                    ]])
                )


            chars[line_no].add(t)

            char_index_counter += char_count
            if self.consider_spaces_as_chars:
                # If spaces count as characters, count the extra \n character
                # which separates Paragraph's lines to avoid issues
                char_index_counter += 1
        return chars

    def _set_all_lines_alignments(self, alignment: str):

        for line_no in range(len(self.lines[0])):
            self._change_alignment_for_a_line(alignment, line_no)
        return self

    def _set_line_alignment(self, alignment: str, line_no: int):
        """Function to set one line's alignment to a specific value.

        Parameters
        ----------
        alignment
            Defines the alignment of paragraph. Possible values are "left", "right", "center".
        line_no
            Defines the line number for which we want to set given alignment.
        """
        self._change_alignment_for_a_line(alignment, line_no)
        return self

    def _set_all_lines_to_initial_positions(self):
        """Set all lines to their initial positions."""
        self.lines[1] = [None] * len(self.lines[0])
        for line_no in range(len(self.lines[0])):
            self[line_no].move_to(
                self.get_center() + self.lines_initial_positions[line_no],
            )
        return self

    def _set_line_to_initial_position(self, line_no: int):
        """Function to set one line to initial positions.

        Parameters
        ----------
        line_no
            Defines the line number for which we want to set given alignment.
        """
        self.lines[1][line_no] = None
        self[line_no].move_to(self.get_center() + self.lines_initial_positions[line_no])
        return self

    def _change_alignment_for_a_line(self, alignment: str, line_no: int) -> None:
        """Function to change one line's alignment to a specific value.

        Parameters
        ----------
        alignment
            Defines the alignment of paragraph. Possible values are "left", "right", "center".
        line_no
            Defines the line number for which we want to set given alignment.
        """
        self.lines[1][line_no] = alignment
        if self.lines[1][line_no] == "center":
            self[line_no].move_to(
                np.array([self.get_center()[0], self[line_no].get_center()[1], 0]),
            )
        elif self.lines[1][line_no] == "right":
            self[line_no].move_to(
                np.array(
                    [
                        self.get_right()[0] - self[line_no].get_width() / 2,
                        self[line_no].get_center()[1],
                        0,
                    ],
                ),
            )
        elif self.lines[1][line_no] == "left":
            self[line_no].move_to(
                np.array(
                    [
                        self.get_left()[0] + self[line_no].get_width() / 2,
                        self[line_no].get_center()[1],
                        0,
                    ],
                ),
            )
