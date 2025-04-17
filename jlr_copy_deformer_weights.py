#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
jlr_copy_deformer_weights.py

描述：
    该工具用于将一个物体上变形器的权重复制到另一个物体上，支持不同类型变形器的权重拷贝，
    并对大量顶点的拷贝进行了效率优化。同时新增批量复制功能——针对软变形器（softMod），
    用户可选中多个目标物体（例如 B、C）并加选源物体（A），程序会根据传入的过滤参数（例如 "softMod"），
    查找源物体上所有符合条件的变形器，并逐个判断各目标物体是否也存在相同名称的变形器，
    若存在则自动进行权重传递。

作者：Juan Lara（修改及优化版本）
版本：1.1
"""
# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
jlr_copy_deformer_weights.py

描述：
    该工具用于将一个物体上变形器的权重复制到另一个物体上，
    支持不同类型变形器之间的权重拷贝，并对大量顶点的赋值过程进行了效率优化。

    此外，还新增了批量复制 softMod 权重的功能：
      - 例如当源物体 A 上有多个 softMod 变形器时，
        用户选中多个目标物体（B、C 等），并附带选中源物体 A，
        系统会根据传入的过滤条件（例如 "softMod"），
        在 A 上查找所有符合条件的变形器，
        并依次检查每个目标物体的变形历史中是否存在与 A 上同名的变形器，
        若存在则调用权重复制操作。

    注意：函数 transfer_deformer_weights 接受的参数均为 PyNode 对象，可通过如下方式调用：
data = {"geo_source": pm.PyNode('sunshangxiang_head'),
        "geo_target": pm.PyNode('sunshangxiang_L_eyeshadow1'),
        "deformer_source": pm.PyNode('softMod3'),
        "deformer_target": pm.PyNode('softMod3'),
        "surface_association": "closestPoint",
        "interface": None,
        }
transfer_deformer_weights(**data)

################################
data = {"source_obj": pm.PyNode('sunshangxiang_head'),
                "target_objs": [pm.PyNode('sunshangxiang_L_eyeshadow1'),pm.PyNode('sunshangxiang_hair_a3_mesh'),pm.PyNode('sunshangxiang_hair_a4_mesh')],
                "surface_association": "closestPoint",
                "interface": None,
                }
batch_transfer_softmod_weights(**data)
作者：Juan Lara（修改及优化版本）
版本：1.2
"""

import sys
import pymel.core as pm
import numpy as np

# 兼容 Python2 与 Python3 的 reload 处理
if sys.version_info.major == 2:
    from imp import reload
else:
    from importlib import reload


def transfer_deformer_weights( geo_source, geo_target=None, deformer_source=None, deformer_target=None,
                               surface_association="closestPoint", interface=None ):
    """
    单次复制：
    将源物体上指定变形器的权重复制到目标物体上对应变形器的权重。

    参数：
      geo_source (PyNode)：源几何体（例如：pm.PyNode('sunshangxiang_head')）
      geo_target (PyNode)：目标几何体；若为空则默认为源物体
      deformer_source (PyNode)：源变形器（例如：pm.PyNode('softMod1')）
      deformer_target (PyNode)：目标变形器
      surface_association (str)：表面关联方式，有效值："closestPoint", "rayCast", "closestComponent"
      interface：UI 接口（用于进度条更新，可设为 None）

    调用示例：
        transfer_deformer_weights(**data)
        （data 中各项均为 PyNode 或相应字符串、None）
    """
    assert geo_source and deformer_source and deformer_target, \
        "请先选择源与目标物体及对应的变形器"

    previous_selection = pm.selected()

    if not geo_target:
        geo_target = geo_source

    if interface:
        interface.progress_bar_init()
        interface.progress_bar_next()

    source_weight_list = get_weight_list(deformer_source, geo_source)
    if not source_weight_list:
        pm.warning("变形器 {} 在 {} 上没有权重列表".format(deformer_source, geo_source))
        if interface:
            interface.progress_bar_ends(message="Finished with errors!")
        return

    target_weight_list = get_weight_list(deformer_target, geo_target)
    if not target_weight_list:
        pm.warning("变形器 {} 在 {} 上没有权重列表".format(deformer_target, geo_target))
        if interface:
            interface.progress_bar_ends(message="Finished with errors!")
        return

    # 初始化目标权重列表（将所有顶点权重设为 1）
    initialize_weight_list(target_weight_list, geo_target)

    if interface:
        interface.progress_bar_next()
    tmp_source = pm.duplicate(geo_source)[0]
    tmp_target = pm.duplicate(geo_target)[0]
    pm.rename(tmp_source, tmp_source.nodeName() + "_cdw_DUP")
    pm.rename(tmp_target, tmp_target.nodeName() + "_cdw_DUP")
    tmp_source.v.set(True)
    tmp_target.v.set(True)

    if interface:
        interface.progress_bar_next()
    pm.select(clear=True)
    l_jnt = list()
    l_jnt.append(pm.joint(n="jnt_tmpA_01", p=[0, 0, 0]))
    l_jnt.append(pm.joint(n="jnt_tmpA_02", p=[0, 1, 0]))
    skin_source = pm.skinCluster(l_jnt, tmp_source, nw=1)
    skin_target = pm.skinCluster(l_jnt, tmp_target, nw=1)

    if interface: interface.progress_bar_next()
    skin_source.setNormalizeWeights(0)
    pm.skinPercent(skin_source, tmp_source, nrm=False, prw=100)
    skin_source.setNormalizeWeights(True)
    n_points = len(geo_source.getShape().getPoints())
    if deformer_source.type() == "blendShape":
        [skin_source.wl[i].w[0].set(source_weight_list.baseWeights[i].get()) for i in range(n_points)]
        [skin_source.wl[i].w[1].set(1.0 - source_weight_list.baseWeights[i].get()) for i in range(n_points)]
    else:
        [skin_source.wl[i].w[0].set(source_weight_list.weights[i].get()) for i in range(n_points)]
        [skin_source.wl[i].w[1].set(1.0 - source_weight_list.weights[i].get()) for i in range(n_points)]

    if interface: interface.progress_bar_next()
    pm.copySkinWeights(ss=skin_source, ds=skin_target, nm=True, sa=surface_association)

    if interface: interface.progress_bar_next()
    tmp_shape = skin_target.getGeometry()[0]
    deformer_target_weights = [v for v in skin_target.getWeights(tmp_shape, 0)]
    [target_weight_list.weights[i].set(val) for i, val in enumerate(deformer_target_weights)]

    if interface: interface.progress_bar_next()
    pm.delete([tmp_source, tmp_target, l_jnt])
    pm.select(previous_selection)

    if interface:
        interface.progress_bar_next()
        interface.progress_bar_ends(message="Finished successfully!")


def get_weight_list( in_deformer, in_mesh ):
    """
    根据物体的 Shape 节点和变形器历史，获取对应的权重列表。
    返回值为 weightList 对象。
    """
    for shape in [in_mesh.getShape()]:
        n_points = len(shape.getPoints())
        for index, each_input in enumerate(in_deformer.input):
            l_connections = each_input.inputGeometry.listConnections(s=1, d=0)
            if l_connections:
                l_history = l_connections[0].listHistory(f=1)
                l_mesh = list(filter(lambda x: type(x) == type(shape), l_history))
                l_mesh = [str(mesh.nodeName()) for mesh in l_mesh]
                if [str(shape.nodeName())] == l_mesh:
                    if in_deformer.type() == "blendShape":
                        weight_list = in_deformer.inputTarget[0].baseWeights
                        return weight_list
                    if not in_deformer.weightList[index]:
                        initialize_weight_list(in_deformer.weightList[index], in_mesh)
                    weight_list = in_deformer.weightList[index]
                    existing_weight_indexes = {w.index() for w in weight_list.weights}
                    for pt_index in range(n_points):
                        if pt_index not in existing_weight_indexes:
                            # 这里假定 weight_list 提供 addWeight 方法来添加缺失的权重对象
                            # 如果没有，则需要采用其他方式创建权重信息（例如扩展权重数组）
                            print (pt_index)
                            weight_list.weights[index].set(0)
                    temp = {w.index() for w in weight_list.weights}
                    print (len(temp))
                    return weight_list


def initialize_weight_list( weight_list, in_mesh ):
    """
    初始化权重列表，将所有顶点权重设置为 1。
    """
    n_points = len(in_mesh.getShape().getPoints())
    [weight_list.weights[i].set(1) for i in range(n_points)]


def get_deformer_list( obj ):
    """
    获取物体 obj 上所有与变形相关的节点，
    过滤类型包括： "ffd"、"wire"、"cluster"、"softMod"、"deltaMush"、"textureDeformer"、"nonLinear"。
    返回一个包含所有符合条件的变形器的列表。
    """
    deformer_types = ["ffd", "wire", "cluster", "softMod", "deltaMush", "textureDeformer", "nonLinear"]
    deformers = []
    if pm.objExists(obj):
        for shape in obj.getShapes():
            hist = pm.listHistory(shape, ha=1, il=1, pdo=1) or []
            for node in hist:
                if node.type() in deformer_types and node not in deformers:
                    deformers.append(node)
    return deformers


def batch_transfer_softmod_weights( source_obj, target_objs, deformer_filter="softMod",
                                    surface_association="closestPoint", interface=None ):
    """
    批量拷贝 softMod 类型（或名称中包含指定关键字）的变形器权重。

    流程：
      1. 在源物体（A）上查找所有名称中包含 deformer_filter（例如 "softMod"）的变形器；
      2. 对于每个目标物体（B、C 等），在其变形历史中查找是否存在与源物体上同名的变形器；
      3. 如果找到匹配，则调用 transfer_deformer_weights 进行权重复制。

    参数：
      source_obj (PyNode)：源物体，例如 pm.PyNode('A')
      target_objs (list[PyNode])：目标物体列表，例如 [pm.PyNode('B'), pm.PyNode('C')]
      deformer_filter (str)：用于过滤变形器名称的字符串（例如 "softMod"，不区分大小写）
      surface_association (str)：表面关联方式，默认 "closestPoint"
      interface：UI 接口（用于进度条显示，可设为 None）
    """
    # 获取源物体上名称中包含 deformer_filter 的所有变形器
    source_deformers = [d for d in get_deformer_list(source_obj) if deformer_filter.lower() in d.nodeName().lower()]
    print(source_deformers)
    if not source_deformers:
        pm.warning("源物体 {} 上未找到名称包含 '{}' 的变形器".format(source_obj, deformer_filter))
        return

    # 遍历所有目标物体
    for target in target_objs:
        target_deformers = get_deformer_list(target)
        print(target_deformers)
        # 对于每个源变形器，检查目标物体是否存在同名变形器
        for s_deformer in source_deformers:
            matching = [t for t in target_deformers if t.nodeName() == s_deformer.nodeName()]
            print(source_obj, target, s_deformer, matching[0])
            if matching:
                transfer_deformer_weights(geo_source=source_obj, geo_target=target,
                                          deformer_source=s_deformer,
                                          deformer_target=matching[0],
                                          surface_association=surface_association,
                                          interface=interface)
            else:
                pm.warning("目标物体 {} 的变形历史中未找到与源变形器 {} 匹配的项".format(target, s_deformer.nodeName()))


def open_copy_deformer_weights():
    """
    打开复制变形器权重的 UI 界面，
    并将 transfer_deformer_weights 函数绑定到 UI 中（用于单次操作）。
    """
    import jlr_copy_deformer_weights_UI as cdwUI
    reload(cdwUI)
    ui = cdwUI.CopyDeformerWeightsUI()
    ui.transfer_function = transfer_deformer_weights
    ui.show()


if __name__ == '__main__':
    # 如以独立方式启动工具，可将脚本所在目录添加到 sys.path 后启动 UI
    module_path = "D:/Development/Maya/jlr_copy_deformer_weights"  # 修改为你的脚本目录
    if module_path not in sys.path:
        sys.path.append(module_path)
    open_copy_deformer_weights()
