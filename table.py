import itertools as it
from typing import Iterable, Sequence, Callable, Any 

# --- ManimGL Core Imports ---
from manimlib.constants import *
from manimlib.mobject.mobject import Mobject
from manimlib.mobject.types.vectorized_mobject import VMobject, VGroup
from manimlib.mobject.geometry import Line, Polygon, Rectangle
from manimlib.mobject.svg.text_mobject import Text
from manimlib import Tex
from manimlib.utils.color import Color

# --- ManimGL Animation Imports ---
from manimlib.animation.animation import Animation
from manimlib.animation.creation import ShowCreation
from manimlib.animation.creation import Write
from manimlib.animation.fading import FadeIn
from manimlib.animation.composition import AnimationGroup

# --- ManimGL Aliases for ManimCE compatibility ---
Create = ShowCreation 

from fractions import Fraction
def process_fraction(fraction:Fraction):
    try:
        if fraction.denominator==1:
            return fraction.numerator
        return fr"{'-' if fraction.numerator < 0 else ''}\frac{{{abs(fraction.numerator)}}}{{{fraction.denominator}}}"
    except:
        return fraction
# --- ManimGL Color Utility ---
def _to_color(color_spec: Any) -> Color:
    """Converts a color specification to a ManimGL Color object."""
    if isinstance(color_spec, Color):
        return color_spec
    return Color(color_spec)

# --- Background Rectangle Utility (Handles cell filling and import compatibility) ---
def BackgroundRectangle_Wrapper(cell_polygon: Polygon, color: Any, opacity: float = 0.8, **kwargs) -> Polygon:
    """
    Creates a filled Polygon from the cell boundaries (returned by get_cell_b) 
    to act as the background.
    """
    # Filter stroke_width to avoid TypeError if it comes from kwargs
    if 'stroke_width' in kwargs:
        del kwargs['stroke_width'] 

    # Set fill properties on the Polygon object
    cell_polygon.set_fill(color=_to_color(color), opacity=opacity) # <-- Uses opacity
    cell_polygon.set_stroke(width=0)
    
    return cell_polygon
# ----------------------------------------------------------------------

class Table(VGroup):
    # List of all custom arguments that should NOT be passed to the parent Mobject constructor
    CUSTOM_TABLE_KWARGS = [
        "row_labels", "col_labels", "top_left_entry", 
        "v_buff", "h_buff", "include_outer_lines", 
        "add_background_rectangles_to_entries", "entries_background_color", 
        "entries_background_opacity", # <-- FIXED: Added missing argument
        "include_background_rectangle", "background_rectangle_color", 
        "element_to_mobject", "element_to_mobject_config", 
        "arrange_in_grid_config", "line_config"
    ]

    def __init__(
        self,
        table: Iterable[Iterable[float | str | VMobject]],
        row_labels: Iterable[VMobject] | None = None,
        col_labels: Iterable[VMobject] | None = None,
        top_left_entry: VMobject | None = None,
        v_buff: float = 0.4,
        h_buff: float = .8,
        include_outer_lines: bool = True,
        math_table : bool =True,
        add_background_rectangles_to_entries: bool = False,
        entries_background_color: Any = BLACK,
        entries_background_opacity: float = 0.2,
        include_background_rectangle: bool = False,
        background_rectangle_color: Any = BLACK,
        element_to_mobject: Callable[[float | str | VMobject], VMobject] = Text,
        element_to_mobject_config: dict = {},
        arrange_in_grid_config: dict = {},
        line_config: dict = {},
        **kwargs,
    ):
        
        # 1. Assign custom attributes (for internal use)
        self.row_labels = row_labels
        self.col_labels = col_labels
        self.top_left_entry = top_left_entry
        self.math_table=math_table
        self.v_buff = v_buff
        self.h_buff = h_buff
        self.include_outer_lines = include_outer_lines
        self.add_background_rectangles_to_entries = add_background_rectangles_to_entries
        self.entries_background_color = _to_color(entries_background_color)
        self.entries_background_opacity = entries_background_opacity # <-- Store the opacity
        self.include_background_rectangle = include_background_rectangle
        self.background_rectangle_color = _to_color(background_rectangle_color)
        self.element_to_mobject = element_to_mobject
        self.element_to_mobject_config = element_to_mobject_config
        self.arrange_in_grid_config = arrange_in_grid_config
        self.line_config = line_config
        self.highlights={}
        if not table:
             raise ValueError("Table cannot be empty.")
        self.row_dim = len(table)
        self.col_dim = len(table[0])

        for row in table:
            if len(row) != self.col_dim:
                raise ValueError("Not all rows in table have the same length.")

        # 2. Filter custom attributes from kwargs before calling super().__init__
        mobject_kwargs = {k: v for k, v in kwargs.items() if k not in self.CUSTOM_TABLE_KWARGS}
        super().__init__(**mobject_kwargs) 
        
        # 3. Build and arrange the table structure
        mob_table = self._table_to_mob_table(table)
        self.elements_without_labels = VGroup(*it.chain(*mob_table))
        
        mob_table = self._add_labels(mob_table) 
        self._organize_mob_table(mob_table)
        self.elements = VGroup(*it.chain(*mob_table))
        self.num_rows=len(mob_table)
        self.num_cols=len(mob_table[0])
        # Remove dummy mobject placeholder if present at index 0 (used for top-left cell)
        if len(self.elements) > 0 and isinstance(self.elements[0], Text) and not self.elements[0].text:
             self.elements.remove(self.elements[0]) 

        self.add(self.elements)
        self.center()
        self.mob_table = mob_table
        
        # 4. Add lines and background
        self._add_horizontal_lines()
        self._add_vertical_lines()
        
        if self.add_background_rectangles_to_entries:
            # Pass color and stored opacity
            self.add_background_to_entries(
                color=self.entries_background_color, 
                opacity=self.entries_background_opacity # <-- Pass the stored opacity
            )
        
        if self.include_background_rectangle:
            # Add a single background rectangle for the entire table using a base Rectangle
            bg_rect = Rectangle(
                width=self.get_width() + self.h_buff, 
                height=self.get_height() + self.v_buff,
                fill_color=self.background_rectangle_color,
                fill_opacity=1.0, 
                stroke_width=0,
            )
            bg_rect.move_to(self)
            self.add_to_back(bg_rect)
            self.background_rectangle = bg_rect


    def _table_to_mob_table(
        self,
        table: Iterable[Iterable[float | str | VMobject]],
    ) -> list:
        # Converts all entries into Mobjects (using Text for strings/floats)
        return [
            [
                item if isinstance(item, VMobject) 
                else  Tex(str(process_fraction(item))) if self.math_table else self.element_to_mobject(str(item), **self.element_to_mobject_config)
                for item in row
            ]
            for row in table
        ]

    def _organize_mob_table(self, table: Iterable[Iterable[VMobject]]) -> VGroup:
        # Flattens table and arranges it into a grid
        help_table = VGroup(*it.chain(*table))
        
        num_rows = len(table)
        num_cols = len(table[0])

        # ManimGL v1.7.2 expects rows and cols as positional arguments for arrange_in_grid
        config = {
            "h_buff": self.h_buff,
            "v_buff": self.v_buff,
            **self.arrange_in_grid_config,
        }
        
        help_table.arrange_in_grid(
            num_rows, 
            num_cols, 
            **config # Pass only the buff and other standard kwargs
        )
        
        return help_table

    def _add_labels(self, mob_table: list[list[VMobject]]) -> list[list[VMobject]]:
        
        if self.row_labels is not None:
            for k in range(len(self.row_labels)):
                mob_table[k].insert(0, self.row_labels[k])
                
        if self.col_labels is not None:
            col_labels_list = list(self.col_labels)
            
            if self.row_labels is not None:
                if self.top_left_entry is not None:
                    col_labels_row = [self.top_left_entry] + col_labels_list
                    mob_table.insert(0, col_labels_row)
                else:
                    # Dummy Mobject placeholder for top-left cell
                    dummy_mobject = Text("", font_size=0.01) 
                    col_labels_row = [dummy_mobject] + col_labels_list
                    mob_table.insert(0, col_labels_row)
            else:
                mob_table.insert(0, col_labels_list)
                
        return mob_table

    def _add_horizontal_lines(self) -> 'Table':
        """Adds the horizontal lines to the table."""
        rows_group = self.get_rows()
        if not rows_group: return self
        
        anchor_left = self.get_left()[0] - 0.5 * self.h_buff
        anchor_right = self.get_right()[0] + 0.5 * self.h_buff
        
        line_group = VGroup()
        
        if self.include_outer_lines:
            # Outer Top Line
            anchor = rows_group[0].get_top()[1] + 0.5 * self.v_buff
            line_group.add(Line([anchor_left, anchor, 0], [anchor_right, anchor, 0], **self.line_config))
            # Outer Bottom Line
            anchor = rows_group[-1].get_bottom()[1] - 0.5 * self.v_buff
            line_group.add(Line([anchor_left, anchor, 0], [anchor_right, anchor, 0], **self.line_config))
            
        # Inner Horizontal Lines
        for k in range(len(rows_group) - 1):
            top_y = rows_group[k].get_bottom()[1]
            bottom_y = rows_group[k + 1].get_top()[1]
            anchor = (top_y + bottom_y) / 2
            line_group.add(Line([anchor_left, anchor, 0], [anchor_right, anchor, 0], **self.line_config))
            
        self.horizontal_lines = line_group
        self.add(line_group)
        return self

    def _add_vertical_lines(self) -> 'Table':
        """Adds the vertical lines to the table"""
        columns_group = self.get_columns()
        if not columns_group: return self
        rows_group = self.get_rows()

        anchor_top = rows_group.get_top()[1] + 0.5 * self.v_buff
        anchor_bottom = rows_group.get_bottom()[1] - 0.5 * self.v_buff
        
        line_group = VGroup()
        
        if self.include_outer_lines:
            # Outer Left Line
            anchor = columns_group[0].get_left()[0] - 0.5 * self.h_buff
            line_group.add(Line([anchor, anchor_top, 0], [anchor, anchor_bottom, 0], **self.line_config))
            # Outer Right Line
            anchor = columns_group[-1].get_right()[0] + 0.5 * self.h_buff
            line_group.add(Line([anchor, anchor_top, 0], [anchor, anchor_bottom, 0], **self.line_config))
            
        # Inner Vertical Lines
        for k in range(len(columns_group) - 1):
            right_x = columns_group[k].get_right()[0]
            left_x = columns_group[k + 1].get_left()[0]
            anchor = (right_x + left_x) / 2
            line_group.add(Line([anchor, anchor_bottom, 0], [anchor, anchor_top, 0], **self.line_config))
            
        self.vertical_lines = line_group
        self.add(line_group)
        return self

    # --- Utility Getters ---
    
    def get_horizontal_lines(self) -> VGroup:
        return self.horizontal_lines

    def get_vertical_lines(self) -> VGroup:
        return self.vertical_lines

    def get_columns(self) -> VGroup:
        if not self.mob_table: return VGroup()
        return VGroup(
            *(
                VGroup(*(row[i] for row in self.mob_table))
                for i in range(len(self.mob_table[0]))
            )
        )

    def get_rows(self) -> VGroup:
        if not self.mob_table: return VGroup()
        return VGroup(*(VGroup(*row) for row in self.mob_table))

    def set_column_colors(self, *colors: Iterable[Any]) -> 'Table':
        columns = self.get_columns()
        for color_spec, column in zip(colors, columns):
            column.set_color(_to_color(color_spec))
        return self

    def set_row_colors(self, *colors: Iterable[Any]) -> 'Table':
        rows = self.get_rows()
        for color_spec, row in zip(colors, rows):
            row.set_color(_to_color(color_spec))
        return self

    def get_entries(self, pos: Sequence[int] | None = None) -> VMobject | VGroup:
        """Gets a cell Mobject from the full mob_table (including labels) using 1-indexing."""
        if pos is not None:
            # pos is 1-indexed (row, col)
            effective_row = pos[0] - 1
            effective_col = pos[1] - 1
            
            try:
                return self.mob_table[effective_row][effective_col]
            except IndexError:
                raise IndexError(
                    f"Invalid position {pos}. Table dimensions (including labels): "
                    f"({len(self.mob_table)} rows, {len(self.mob_table[0])} cols)."
                )
        else:
            return self.elements

    def get_entries_without_labels(self, pos: Sequence[int] | None = None) -> VMobject | VGroup:
        """Gets an entry from the original data (excluding labels) using 1-indexing."""
        if pos is not None:
            index = self.col_dim * (pos[0] - 1) + pos[1] - 1
            return self.elements_without_labels[index]
        else:
            return self.elements_without_labels

    def get_row_labels(self) -> VGroup:
        return VGroup(*(self.row_labels or []))

    def get_col_labels(self) -> VGroup:
        return VGroup(*(self.col_labels or []))

    def get_labels(self) -> VGroup:
        label_group = VGroup()
        if self.top_left_entry is not None:
            label_group.add(self.top_left_entry)
        if self.col_labels is not None:
            label_group.add(*self.col_labels)
        if self.row_labels is not None:
            label_group.add(*self.row_labels)
        return label_group

    def add_background_to_entries(self, color: Any = BLACK, opacity: float = 1.0) -> 'Table':
        """Adds a background that spans the whole cell of each original data entry."""
        
        # Iterate over the original data rows and columns (excluding labels)
        for r_data_idx in range(self.row_dim):
            for c_data_idx in range(self.col_dim):
                # 1-indexed position of the original data entry (starting from 1, 1)
                data_pos = (r_data_idx + 1, c_data_idx + 1)
                
                # Retrieve the original data Mobject (used for animation/reference)
                entry = self.get_entries_without_labels(data_pos)

                # Calculate the cell position in the full mob_table (including labels)
                row_shift = 1 if self.col_labels is not None else 0
                col_shift = 1 if self.row_labels is not None else 0
                full_pos = (r_data_idx + 1 + row_shift, c_data_idx + 1 + col_shift)

                # Use get_cell_b with the shifted position to get the exact boundary
                cell_boundaries = self.get_cell_b(full_pos)
                
                # Create the filled background Polygon (fills the whole cell area)
                # Pass the provided opacity
                bg_rect = BackgroundRectangle_Wrapper(cell_boundaries, color=_to_color(color), opacity=opacity)
                
                # Attach the background to the entry and add it to the table (at the back)
                entry.background_rectangle = bg_rect
                self.add_to_back(bg_rect)
        return self
        
    def get_cell(self, pos: Sequence[int] = (1, 1), **kwargs):
        return self.mob_table[pos[0]][pos[1]]
    
    def get_cell_b(self, pos: Sequence[int] = (1, 1), **kwargs) -> Polygon:
        row = self.get_rows()[pos[0]]
        col = self.get_columns()[pos[1]]
        
        # Calculate the four corners of the cell polygon
        edge_UL = [col.get_left()[0] - self.h_buff / 2, row.get_top()[1] + self.v_buff / 2, 0]
        edge_UR = [col.get_right()[0] + self.h_buff / 2, row.get_top()[1] + self.v_buff / 2, 0]
        edge_DR = [col.get_right()[0] + self.h_buff / 2, row.get_bottom()[1] - self.v_buff / 2, 0]
        edge_DL = [col.get_left()[0] - self.h_buff / 2, row.get_bottom()[1] - self.v_buff / 2, 0]
        
        rec = Polygon(edge_UL, edge_UR, edge_DR, edge_DL, **kwargs)
        return rec

    def get_highlighted_cell(
        self, pos: Sequence[int] = (1, 1), color: Any = YELLOW, opacity:float=0.8, **kwargs
    ) -> Polygon:
        # Returns a filled Polygon (cell) which acts as the highlight
        cell = self.get_cell_b(pos)
        cell.set_fill(color=_to_color(color), opacity=opacity)
        cell.set_stroke(width=0)
        return cell 

    def add_highlighted_cell(
        self, pos: Sequence[int] = (1, 1), color: Any = YELLOW, **kwargs
    ) -> 'Table':
        bg_cell = self.get_highlighted_cell(pos, color=_to_color(color), **kwargs)
        self.highlights[f'{pos}']=bg_cell
        self.add_to_back(bg_cell)
        
        entry = self.get_entries(pos)
        entry.background_rectangle = bg_cell # Attach for animation reference
        return self
    
    def remove_highlighted_cell(self, pos: Sequence[int] = (1, 1),) -> None:
        if f'{pos}' in self.highlights:
            self.remove(self.highlights[f'{pos}'])
    
    def remove_highlighted_cells(self) -> None:
        self.remove(self.highlights)
    

    
    
    def create_lines(
        self,
        lag_ratio: float = 1,
        line_animation: Callable[[VMobject | VGroup], Animation] = Create,
        **kwargs
        ):
        animations: Sequence[Animation] = []
        
        # Lines
        if hasattr(self, 'vertical_lines') and hasattr(self, 'horizontal_lines'):
            animations.append(
                line_animation(
                    VGroup(self.vertical_lines, self.horizontal_lines),
                    **kwargs,
                )
            )
        return AnimationGroup(*animations, lag_ratio=lag_ratio)
    
    def create_lables(
        self,
        lag_ratio: float = 1,
        line_animation: Callable[[VMobject | VGroup], Animation] = Create,
        label_animation: Callable[[VMobject | VGroup], Animation] = Write,
        element_animation: Callable[[VMobject | VGroup], Animation] = Create,

        **kwargs
        ):
        animations: Sequence[Animation] = []
        
        # Lines
        if hasattr(self, 'vertical_lines') and hasattr(self, 'horizontal_lines'):
            animations.append(
                line_animation(
                    VGroup(self.vertical_lines, self.horizontal_lines),
                    **kwargs,
                )
            )
        if self.elements_without_labels:
            animations.append(label_animation(VGroup(*[*self.get_rows()[0],*self.get_columns()[0]]), **kwargs))
            # animations.append(element_animation(self.elements_without_labels))

        labels = self.get_labels()
        if labels:
            animations.append(label_animation(labels, **kwargs))
        
        return AnimationGroup(*animations, lag_ratio=lag_ratio)
    
    def create_row(self,
        row : int = 0,
        lag_ratio: float = 1,
        exclude : int | None = None,
        element_animation: Callable[[VMobject | VGroup], Animation] = Write,
        **kwargs,
        ):
        animations: Sequence[Animation] = []
        rows = self.get_rows()
        if rows:
            if exclude == None:
                elements=rows[row]
            else:
                elements=VGroup(rows[row][:exclude],rows[row][exclude+1:] if exclude+1 < len(rows[row]) else [])
            animations.append(element_animation(elements, **kwargs))
        
        return AnimationGroup(*animations, lag_ratio=lag_ratio)
    
    
    def create_column(self,
        col : int = 0,
        lag_ratio: float = 1,
        exclude : int | None = None,
        element_animation: Callable[[VMobject | VGroup], Animation] = Write,
        **kwargs,
        ):
        animations: Sequence[Animation] = []
        columns = self.get_columns()
        if columns:
            if exclude == None:
                elements=columns[col]
            else:
                elements=VGroup(columns[col][:exclude],columns[col][exclude+1:] if exclude+1 < len(columns[col]) else [])
                
            animations.append(element_animation(elements, **kwargs))
        
        return AnimationGroup(*animations, lag_ratio=lag_ratio)
    
    def create_cell(self,
        pos: Sequence[int] = (1, 1),
        lag_ratio: float = 1,
        element_animation: Callable[[VMobject | VGroup], Animation] = Write,
        **kwargs,
        ):
        animations: Sequence[Animation] = []
        cell = self.get_cell(pos)
        if cell:
            return element_animation(cell, **kwargs)
    
        return AnimationGroup(*animations, lag_ratio=lag_ratio)
    

    def create(
        self,
        lag_ratio: float = 1,
        line_animation: Callable[[VMobject | VGroup], Animation] = Create,
        label_animation: Callable[[VMobject | VGroup], Animation] = Write,
        element_animation: Callable[[VMobject | VGroup], Animation] = Create,
        entry_animation: Callable[[VMobject | VGroup], Animation] = FadeIn,
        **kwargs,
    ) -> AnimationGroup:
        animations: Sequence[Animation] = []
        
        # Lines
        if hasattr(self, 'vertical_lines') and hasattr(self, 'horizontal_lines'):
            animations.append(
                line_animation(
                    VGroup(self.vertical_lines, self.horizontal_lines),
                    **kwargs,
                )
            )

        # Main Data Entries
        if self.elements_without_labels:
            animations.append(element_animation(self.elements_without_labels, **kwargs))

        # Labels
        labels = self.get_labels()
        if labels:
            animations.append(label_animation(labels, **kwargs))

        # Backgrounds
        for entry in self.elements_without_labels:
            if hasattr(entry, 'background_rectangle'):
                animations.append(entry_animation(entry.background_rectangle, **kwargs))

        return AnimationGroup(*animations, lag_ratio=lag_ratio)

    
    def scale(self, scale_factor: float, **kwargs):
        # Scale the buffers to maintain consistent cell appearance after scaling
        self.h_buff *= scale_factor
        self.v_buff *= scale_factor
        super().scale(scale_factor, **kwargs)
        return self