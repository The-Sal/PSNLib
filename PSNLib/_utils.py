from utils3.system import paths

def relativeItem(item, assertExists=True):
    pt = paths.join(__file__.replace(paths.basename(__file__), 'assets'), item)
    if assertExists:
        assert paths.isfile(pt), f'Item {item} does not exist'
    return pt
