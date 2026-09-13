from manimlib import Scene,Text
from . import save_scene_to_svg
import os
import subprocess

class PDFScene(Scene):
    DEFAUL_PDF_FOLDER='PDFScene'
    # Page width in cm; the height follows the camera's aspect ratio
    PDF_PAGE_WIDTH=32

    def __init__(self, window = None, camera_config = ..., file_writer_config = ..., skip_animations = False, always_update_mobjects = False, start_at_animation_number = None, end_at_animation_number = None, show_animation_progress = False, leave_progress_bars = False, preview_while_skipping = True, presenter_mode = False, default_wait_time = 1):
        super().__init__(window, camera_config, file_writer_config, skip_animations, always_update_mobjects, start_at_animation_number, end_at_animation_number, show_animation_progress, leave_progress_bars, preview_while_skipping, presenter_mode, default_wait_time)
        self.pages=[]

    def screenshot(self):
        name=type(self).__name__
        path=f'{self.DEFAUL_PDF_FOLDER}/{name}'
        n=len(self.pages)
        if n==0:
            if self.DEFAUL_PDF_FOLDER not in os.listdir():
                os.mkdir(self.DEFAUL_PDF_FOLDER)

            path=f'{self.DEFAUL_PDF_FOLDER}/{name}'
            if name  not in os.listdir(self.DEFAUL_PDF_FOLDER):
                os.mkdir(path)

        self.pages.append([])
        save_scene_to_svg(self,f'{path}/{n}.svg')


    def compile(self):
        """Builds PDFScene/<Name>/<Name>.pdf from the screenshots with Typst."""
        name=type(self).__name__
        folder=os.path.abspath(f'{self.DEFAUL_PDF_FOLDER}/{name}')
        here=os.path.dirname(os.path.abspath(__file__))
        # Typst only reads files under --root, which must hold both the pages and pdfscene.typ
        root=os.path.commonpath([folder,here])
        helper='/'+os.path.relpath(os.path.join(here,'pdfscene.typ'),root)

        page_height=self.PDF_PAGE_WIDTH*self.camera.get_pixel_height()/self.camera.get_pixel_width()
        typ=[
            f'#import "{helper}": scene-page',
            f'#set page(width: {self.PDF_PAGE_WIDTH}cm, height: {page_height:.4f}cm, margin: 0pt)',
        ]
        for i in range(len(self.pages)):
            typ.append('#pagebreak(weak: true)')
            typ.append(f'#scene-page(read("{i}.svg", encoding: none))')

        typ_path=f'{folder}/{name}.typ'
        with open(typ_path,'w',encoding='utf-8') as f:
            f.write('\n'.join(typ)+'\n')

        pdf_path=f'{folder}/{name}.pdf'
        subprocess.run(
            ['typst','compile','--root',root,'--font-path',os.path.join(here,'fonts'),typ_path,pdf_path],
            check=True,
        )
        print(f'PDF saved to {pdf_path}')
