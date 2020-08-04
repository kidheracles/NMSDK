import struct
from collections import namedtuple

# TODO: move to the serialization folder?

from ..serialization.utils import (read_list_header, read_string, # noqa pylint: disable=relative-beyond-top-level
                                   bytes_to_quat, read_bool)
from ..serialization.list_header import ListHeader  # noqa pylint: disable=relative-beyond-top-level
from ..NMS.LOOKUPS import DIFFUSE, MASKS, NORMAL  # noqa pylint: disable=relative-beyond-top-level


def read_anim(fname):
    """ Reads an anim file. """
    anim_data = dict()

    with open(fname, 'rb') as f:
        f.seek(0x60)
        # get the counts and offsets of all the info
        frame_count, node_count = struct.unpack('<II', f.read(0x8))
        anim_data['FrameCount'] = frame_count
        anim_data['NodeCount'] = node_count
        anim_data['NodeData'] = list()
        # NodeData
        with ListHeader(f) as node_data:
            for _ in range(node_data.count):
                node_name = read_string(f, 0x40)
                # Skip 'can_compress'
                f.seek(0x4, 1)
                rot_index, trans_index, scale_index = struct.unpack(
                    '<III', f.read(0xC))
                data = {'Node': node_name,
                        'RotIndex': rot_index,
                        'TransIndex': trans_index,
                        'ScaleIndex': scale_index}
                anim_data['NodeData'].append(data)
        # AnimFrameData
        anim_data['AnimFrameData'] = list()
        with ListHeader(f) as anim_frame_data:
            for _ in range(anim_frame_data.count):
                frame_data = dict()
                with ListHeader(f) as rot_data:
                    rot_data_lst = list()
                    for _ in range(int(rot_data.count // 3)):
                        rot_data_lst.append(bytes_to_quat(f))
                    frame_data['Rotation'] = rot_data_lst  # reads 0x6 bytes
                with ListHeader(f) as trans_data:
                    trans_data_lst = list()
                    for _ in range(trans_data.count):
                        trans_data_lst.append(
                            struct.unpack('<ffff', f.read(0x10)))
                    frame_data['Translation'] = trans_data_lst
                with ListHeader(f) as scale_data:
                    scale_data_lst = list()
                    for _ in range(scale_data.count):
                        scale_data_lst.append(
                            struct.unpack('<ffff', f.read(0x10)))
                    frame_data['Scale'] = scale_data_lst
                anim_data['AnimFrameData'].append(frame_data)
        # StillFrameData
        still_frame_data = dict()
        with ListHeader(f) as rot_data:
            rot_data_lst = list()
            for _ in range(int(rot_data.count // 3)):
                rot_data_lst.append(bytes_to_quat(f))  # reads 0x6 bytes
            still_frame_data['Rotation'] = rot_data_lst
        with ListHeader(f) as trans_data:
            trans_data_lst = list()
            for _ in range(trans_data.count):
                trans_data_lst.append(
                    struct.unpack('<ffff', f.read(0x10)))
            still_frame_data['Translation'] = trans_data_lst
        with ListHeader(f) as scale_data:
            scale_data_lst = list()
            for _ in range(scale_data.count):
                scale_data_lst.append(
                    struct.unpack('<ffff', f.read(0x10)))
            still_frame_data['Scale'] = scale_data_lst
        anim_data['StillFrameData'] = still_frame_data

        return anim_data


def read_entity(fname):
    """ Read an entity file.

    This will currently only support reading the animation data from the
    entity file as it's all we care about right now...

    Returns
    -------
    anim_data : list
        List of dictionaries containing the path and name of the contained
        animation data.
    """

    anim_data = dict()
    with open(fname, 'rb') as f:
        f.seek(0x60)
        has_anims = False
        # Scan the list of components to see if we have a
        # TkAnimationComponentData struct present.
        with ListHeader(f) as components:
            for _ in range(components.count):
                return_offset = f.tell()
                offset = struct.unpack('<Q', f.read(0x8))[0]
                struct_name = read_string(f, 0x40)
                if struct_name == 'cTkAnimationComponentData':
                    has_anims = True
                    break
                # Read the nameHash but ignore it...
                f.read(0x8)
        # If no animation data is found, return.
        if not has_anims:
            return anim_data
        # Jump to the start of the struct
        f.seek(return_offset + offset)
        _anim_data = read_TkAnimationComponentData(f)
        anim_data[_anim_data.pop('Anim')] = _anim_data
        with ListHeader(f) as anims:
            for _ in range(anims.count):
                _anim_data = read_TkAnimationComponentData(f)
                anim_data[_anim_data.pop('Anim')] = _anim_data
        return anim_data


def read_material(fname):
    """ Reads the textures and types from a material file.

    Returns
    -------
    data : dict
        Mapping between the texture type (one of DIFFUSE, MASKS, NORMAL) and
        the path to the texture
    """
    data = dict()

    # Read the data directly from the mbin
    with open(fname, 'rb') as f:
        f.seek(0x60)
        # get name
        data['Name'] = read_string(f, 0x80)
        # skip metamaterial, introduced in 2.61 - see issue 72
        f.seek(0x100,1)
        # get class
        data['Class'] = read_string(f, 0x20)
        # get whether it casts a shadow
        f.seek(0x4,1)
        data['CastShadow'] = read_bool(f)
        # save pointer for Flags Uniforms Samplers list headers
        list_header_first = f.tell()+0x1+0x80+0x80+0x2
        # get material flags
        data['Flags'] = list()
        f.seek(list_header_first)
        list_offset, list_count = read_list_header(f)
        f.seek(list_offset, 1)
        for i in range(list_count):
            data['Flags'].append(struct.unpack('<I', f.read(0x4))[0])
        # get uniforms
        data['Uniforms'] = dict()
        f.seek(list_header_first+0x10)
        list_offset, list_count = read_list_header(f)
        f.seek(list_offset, 1)
        for i in range(list_count):
            name = read_string(f, 0x20)
            value = struct.unpack('<ffff', f.read(0x10))
            data['Uniforms'][name] = value
            f.seek(0x10, 1)
        # get samplers (texture paths)
        data['Samplers'] = dict()
        f.seek(list_header_first+0x20)
        list_offset, list_count = read_list_header(f)
        f.seek(list_offset, 1)
        for i in range(list_count):
            name = read_string(f, 0x20)
            Map = read_string(f, 0x80)
            data['Samplers'][name] = Map
            if i != list_count - 1:
                f.seek(0x38, 1)

    return data


def read_mesh_binding_data(fname):
    """ Read the data relating to mesh/joint bindings from the geometry file.

    Returns
    -------
    data : dict
        All the relevant data from the geometry file
    """
    data = dict()
    with open(fname, 'rb') as f:
        # First, check that there is data to read. If not, then return nothing
        f.seek(0x78)
        if struct.unpack('<I', f.read(0x4))[0] == 0:
            return
        # Read joint binding data
        f.seek(0x70)
        data['JointBindings'] = list()
        with ListHeader(f) as JointBindings:
            for _ in range(JointBindings.count):
                jb_data = dict()
                fmt = '<' + 'f' * 0x10
                jb_data['InvBindMatrix'] = struct.unpack(fmt, f.read(0x40))
                jb_data['BindTranslate'] = struct.unpack('<fff', f.read(0xC))
                jb_data['BindRotate'] = struct.unpack('<ffff', f.read(0x10))
                jb_data['BindScale'] = struct.unpack('<fff', f.read(0xC))
                data['JointBindings'].append(jb_data)
        # skip to the skin matrix layout data
        f.seek(0xB0)
        with ListHeader(f) as SkinMatrixLayout:
            fmt = '<' + 'I' * SkinMatrixLayout.count
            data_size = 4 * SkinMatrixLayout.count
            data['SkinMatrixLayout'] = struct.unpack(fmt, f.read(data_size))

        # skip to the MeshBaseSkinMat data
        f.seek(0x100)
        with ListHeader(f) as MeshBaseSkinMat:
            fmt = '<' + 'I' * MeshBaseSkinMat.count
            data_size = 4 * MeshBaseSkinMat.count
            data['MeshBaseSkinMat'] = struct.unpack(fmt, f.read(data_size))

    return data


def read_metadata(fname):
    """ Reads all the metadata from the gstream file.

    Returns
    -------
    data : dict (str: namedtuple)
        Mapping between the names of the meshes and their metadata
    """
    data = dict()
    with open(fname, 'rb') as f:
        # move to the start of the StreamMetaDataArray header
        f.seek(0x190)
        # find how far to jump
        list_offset, list_count = read_list_header(f)
        f.seek(list_offset, 1)
        for _ in range(list_count):
            # read the ID in and strip it to be just the string and no padding.
            string = read_string(f, 0x80)
            # skip the hash
            f.seek(0x8, 1)
            # read in the actual data we want
            vert_size, vert_off, idx_size, idx_off = struct.unpack(
                '<IIII',
                f.read(0x10))
            gstream_info = namedtuple('gstream_info',
                                      ['vert_size', 'vert_off',
                                       'idx_size', 'idx_off'])
            if string not in data:
                data[string] = gstream_info(vert_size, vert_off, idx_size,
                                            idx_off)
            else:
                data[string] = [data[string]]
                data[string].append(gstream_info(vert_size, vert_off, idx_size,
                                                 idx_off))
    return data


def read_gstream(fname, info):
    """ Read the requested info from the gstream file.

    Parameters
    ----------
    fname : string
        File path to the ~.GEOMETRY.DATA.MBIN.PC file.
    info : namedtuple
        namedtupled containing the vertex sizes and offset, and index sizes and
        offsets.

    Returns
    -------
    verts : bytes
        Raw vertex data.
    indexes : bytes
        Raw index data.
    """
    with open(fname, 'rb') as f:
        f.seek(info.vert_off)
        verts = f.read(info.vert_size)
        f.seek(info.idx_off)
        indexes = f.read(info.idx_size)
    return verts, indexes


def read_TkAnimationComponentData(f):
    """ Extract the animation name and path from the entity file. """
    data = dict()
    data['Anim'] = read_string(f, 0x10)
    data['Filename'] = read_string(f, 0x80)
    # Move the pointer to the end of the TkAnimationComponentData struct
    f.seek(0xA8, 1)
    return data
