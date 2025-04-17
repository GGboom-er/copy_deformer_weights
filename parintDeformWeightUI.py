#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: parintDeformWeightUI.py
@date: 2025/4/15 13:53
@desc: 
"""
#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: parintDeformWeightUI.py
@date: 2025/4/15 13:53
@desc: 新增变形器类型筛选下拉菜单，默认列出 softMod 变形器，
       可选择 blendShape 或 skinCluster 类型进行筛选，双击进入对应绘制界面。
"""

import maya.cmds as cmds
import maya.mel as mel


def update_deformer_list(*args):
    """
    每当选择变化或下拉菜单切换时更新变形器列表：
    1. 获取当前选中的所有 mesh（包含子节点）。
    2. 根据下拉菜单选择的变形器类型，通过 listHistory 获得网格的历史节点，
       并筛选出相应类型的变形器节点。
    3. 更新文本滚动列表中显示对应类型的变形器名称。
    """
    # 清空文本滚动列表内容
    cmds.textScrollList('deformerList', edit=True, removeAll=True)

    # 查询当前筛选的变形器类型，下拉菜单名称为 "deformerFilterMenu"
    filter_type = cmds.optionMenu("deformerFilterMenu", query=True, value=True)

    # 获取当前选中的 mesh 节点（包括所有层级子节点）
    sel_meshes = cmds.ls(selection=True, dag=True, type='mesh')
    if not sel_meshes:
        cmds.textScrollList('deformerList', edit=True, append='未选中任何 mesh')
        return

    deformer_set = set()
    for mesh in sel_meshes:
        # 获取网格历史节点
        history = cmds.listHistory(mesh) or []
        for node in history:
            # 判断节点类型是否与下拉菜单筛选一致
            if cmds.nodeType(node) == filter_type:
                deformer_set.add(node)

    if not deformer_set:
        cmds.textScrollList('deformerList', edit=True,
                            append='选中 mesh 无 {} 变形器'.format(filter_type))
    else:
        for deformer in sorted(deformer_set):
            cmds.textScrollList('deformerList', edit=True, append=deformer)


def open_deformer_paint_tool(*args):
    """
    双击文本滚动列表中某个变形器时调用：
    1. 获取当前选中的变形器名称。
    2. 根据变形器类型决定调用哪种绘制工具：
       - softMod：使用 artSetToolAndSelectAttr 进入权重绘制界面
       - skinCluster：调用 ArtPaintSkinWeightsToolOptions; paintSkinWeightsChangeSelectMode sunshangxiang_head;
       - blendShape：调用 artSetToolAndSelectAttr 命令进入 blendShape 绘制界面
    """
    # 获取列表中选中的变形器（返回列表）
    sel = cmds.textScrollList('deformerList', query=True, selectItem=True)
    if not sel:
        cmds.warning("请先在列表中选择一个变形器")
        return
    deformer = sel[0]
    node_type = cmds.nodeType(deformer)

    if node_type == 'softMod':
        # 软变形权重绘制
        mel_cmd = 'artSetToolAndSelectAttr("artAttrCtx", "softMod.{0}.weights");'.format(deformer)
        mel.eval(mel_cmd)
    elif node_type == 'skinCluster':
        # 皮肤权重绘制，调用指定命令
        mel.eval('ArtPaintSkinWeightsToolOptions; paintSkinWeightsChangeSelectMode sunshangxiang_head;')
    elif node_type == 'blendShape':
        # blendShape权重绘制
        mel.eval('artSetToolAndSelectAttr("artAttrCtx", "blendShape.parallelBlender.paintTargetWeights");')
    else:
        cmds.warning("暂不支持 {} 类型的变形器绘制".format(node_type))


def create_deformer_window():
    """
    创建窗口并初始化：
    1. 如果窗口已存在，则先删除。
    2. 创建新窗口和 UI 布局，并添加变形器类型下拉菜单及文本滚动列表。
    3. 通过 scriptJob 监听 SelectionChanged 事件和下拉菜单变更，实时更新列表
       （利用 parent 参数绑定 UI，保证窗口关闭时自动销毁对应的 scriptJob）。
    """
    if cmds.window('deformerWindow', exists=True):
        cmds.deleteUI('deformerWindow')

    window = cmds.window('deformerWindow', title="变形器绘制工具", widthHeight=(220, 380))
    cmds.columnLayout(adjustableColumn=True)
    cmds.text(label="筛选变形器类型与双击进入绘制工具", align='center')

    # 新增变形器类型下拉菜单
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnAlign=(1, 'right'), columnWidth=[(1, 90)])
    cmds.text(label="筛选类型:")
    cmds.optionMenu("deformerFilterMenu", changeCommand=lambda x: update_deformer_list())
    cmds.menuItem(label="softMod")
    cmds.menuItem(label="blendShape")
    cmds.menuItem(label="skinCluster")
    cmds.setParent("..")

    # 创建用于显示变形器列表的文本滚动列表，并绑定双击事件
    cmds.textScrollList('deformerList', doubleClickCommand=open_deformer_paint_tool, allowMultiSelection=False, height=280)
    cmds.showWindow(window)

    # 利用 parent 参数将 scriptJob 与窗口绑定
    cmds.scriptJob(event=["SelectionChanged", update_deformer_list], parent=window)


# 执行创建窗口函数
create_deformer_window()

