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
@desc: ��������������ɸѡ�����˵���Ĭ���г� softMod ��������
       ��ѡ�� blendShape �� skinCluster ���ͽ���ɸѡ��˫�������Ӧ���ƽ��档
"""

import maya.cmds as cmds
import maya.mel as mel


def update_deformer_list(*args):
    """
    ÿ��ѡ��仯�������˵��л�ʱ���±������б�
    1. ��ȡ��ǰѡ�е����� mesh�������ӽڵ㣩��
    2. ���������˵�ѡ��ı��������ͣ�ͨ�� listHistory ����������ʷ�ڵ㣬
       ��ɸѡ����Ӧ���͵ı������ڵ㡣
    3. �����ı������б�����ʾ��Ӧ���͵ı��������ơ�
    """
    # ����ı������б�����
    cmds.textScrollList('deformerList', edit=True, removeAll=True)

    # ��ѯ��ǰɸѡ�ı��������ͣ������˵�����Ϊ "deformerFilterMenu"
    filter_type = cmds.optionMenu("deformerFilterMenu", query=True, value=True)

    # ��ȡ��ǰѡ�е� mesh �ڵ㣨�������в㼶�ӽڵ㣩
    sel_meshes = cmds.ls(selection=True, dag=True, type='mesh')
    if not sel_meshes:
        cmds.textScrollList('deformerList', edit=True, append='δѡ���κ� mesh')
        return

    deformer_set = set()
    for mesh in sel_meshes:
        # ��ȡ������ʷ�ڵ�
        history = cmds.listHistory(mesh) or []
        for node in history:
            # �жϽڵ������Ƿ��������˵�ɸѡһ��
            if cmds.nodeType(node) == filter_type:
                deformer_set.add(node)

    if not deformer_set:
        cmds.textScrollList('deformerList', edit=True,
                            append='ѡ�� mesh �� {} ������'.format(filter_type))
    else:
        for deformer in sorted(deformer_set):
            cmds.textScrollList('deformerList', edit=True, append=deformer)


def open_deformer_paint_tool(*args):
    """
    ˫���ı������б���ĳ��������ʱ���ã�
    1. ��ȡ��ǰѡ�еı��������ơ�
    2. ���ݱ��������;����������ֻ��ƹ��ߣ�
       - softMod��ʹ�� artSetToolAndSelectAttr ����Ȩ�ػ��ƽ���
       - skinCluster������ ArtPaintSkinWeightsToolOptions; paintSkinWeightsChangeSelectMode sunshangxiang_head;
       - blendShape������ artSetToolAndSelectAttr ������� blendShape ���ƽ���
    """
    # ��ȡ�б���ѡ�еı������������б�
    sel = cmds.textScrollList('deformerList', query=True, selectItem=True)
    if not sel:
        cmds.warning("�������б���ѡ��һ��������")
        return
    deformer = sel[0]
    node_type = cmds.nodeType(deformer)

    if node_type == 'softMod':
        # �����Ȩ�ػ���
        mel_cmd = 'artSetToolAndSelectAttr("artAttrCtx", "softMod.{0}.weights");'.format(deformer)
        mel.eval(mel_cmd)
    elif node_type == 'skinCluster':
        # Ƥ��Ȩ�ػ��ƣ�����ָ������
        mel.eval('ArtPaintSkinWeightsToolOptions; paintSkinWeightsChangeSelectMode sunshangxiang_head;')
    elif node_type == 'blendShape':
        # blendShapeȨ�ػ���
        mel.eval('artSetToolAndSelectAttr("artAttrCtx", "blendShape.parallelBlender.paintTargetWeights");')
    else:
        cmds.warning("�ݲ�֧�� {} ���͵ı���������".format(node_type))


def create_deformer_window():
    """
    �������ڲ���ʼ����
    1. ��������Ѵ��ڣ�����ɾ����
    2. �����´��ں� UI ���֣�����ӱ��������������˵����ı������б�
    3. ͨ�� scriptJob ���� SelectionChanged �¼��������˵������ʵʱ�����б�
       ������ parent ������ UI����֤���ڹر�ʱ�Զ����ٶ�Ӧ�� scriptJob����
    """
    if cmds.window('deformerWindow', exists=True):
        cmds.deleteUI('deformerWindow')

    window = cmds.window('deformerWindow', title="���������ƹ���", widthHeight=(220, 380))
    cmds.columnLayout(adjustableColumn=True)
    cmds.text(label="ɸѡ������������˫��������ƹ���", align='center')

    # �������������������˵�
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnAlign=(1, 'right'), columnWidth=[(1, 90)])
    cmds.text(label="ɸѡ����:")
    cmds.optionMenu("deformerFilterMenu", changeCommand=lambda x: update_deformer_list())
    cmds.menuItem(label="softMod")
    cmds.menuItem(label="blendShape")
    cmds.menuItem(label="skinCluster")
    cmds.setParent("..")

    # ����������ʾ�������б���ı������б�����˫���¼�
    cmds.textScrollList('deformerList', doubleClickCommand=open_deformer_paint_tool, allowMultiSelection=False, height=280)
    cmds.showWindow(window)

    # ���� parent ������ scriptJob �봰�ڰ�
    cmds.scriptJob(event=["SelectionChanged", update_deformer_list], parent=window)


# ִ�д������ں���
create_deformer_window()

