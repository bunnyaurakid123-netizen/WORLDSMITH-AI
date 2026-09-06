from pathlib import Path

def inspect_world(path:Path)->str:
    region=path/'region'
    count=len(list(region.glob('*.mca'))) if region.is_dir() else 0
    return f'World path: {path}\nlevel.dat: {"yes" if (path/"level.dat").exists() else "no"}\nregion directory: {"yes" if region.exists() else "no"}\nregion files: {count}'
