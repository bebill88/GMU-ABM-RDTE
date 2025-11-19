from pathlib import Path
path=Path('README.md')
text=path.read_bytes().decode('cp1252')
text=text.replace('—','-')
text=text.replace('–','-')
text=text.replace('’',"'")
text=text.replace('“','"')
text=text.replace('”','"')
path.write_text(text, encoding='utf-8')
