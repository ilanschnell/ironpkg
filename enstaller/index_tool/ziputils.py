import time
import zipfile


def writestr(z, arcname, data):
    zinfo = zipfile.ZipInfo(filename=arcname,
                            date_time=time.localtime(time.time()))
    # 0x81b6 is what os.stat('file.txt')[0] returns on Linux, where
    # file.txt has mode 0666.
    zinfo.external_attr = 0x81b6 << 16
    z.writestr(zinfo, data)


def zip_repack(zip_src, zip_dst, arc_map={}):
    """
    Repacks a zip-file 'zip_src' to a new zipfile 'zip_dst' with
    updated (or inserted) archives given by 'arc_map'.

    arc_map:
        a dictionary mapping archive names to their content.
        If an archive name maps to None, it is not created in the
        repacked zip-file.
    """
    # zip_src: y   ->   zip_dst: z
    y = zipfile.ZipFile(zip_src)
    z = zipfile.ZipFile(zip_dst, 'w', zipfile.ZIP_DEFLATED)

    # First write all archives from y into z, except the ones which get
    # overwritten (if any).
    for name in y.namelist():
        if name not in arc_map:
            z.writestr(y.getinfo(name), y.read(name))

    # Now, write the new archives.
    for arcname, data in arc_map.iteritems():
        if data is not None:
            writestr(z, arcname, data)

    z.close()
    y.close()


def zip_select(zip_file, arcname):
    """
    Return the content of arcname from a zip-file, or None if the arcname
    does not exist.
    """
    z = zipfile.ZipFile(zip_file)
    if arcname not in z.namelist():
        z.close()
        return None
    data = z.read(arcname)
    z.close()
    return data
