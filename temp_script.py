# -*- coding: utf-8 -*-
from pathlib import Path
path=Path('README.md')
text=path.read_text(encoding='utf-8')
text=text.replace('\u2013','-')
text=text.replace('\u2014','--')
text=text.replace('\u2019',"'")
text=text.replace('\u201c','\"')
text=text.replace('\u201d','\"')
path.write_text(text, encoding='utf-8')
