# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#Node Controls
#Copyright (C) 2023 Pablo Tochez Anderson, Other Realms
#contact@pablotochez.com

bl_info = {
    "name" : "Node Controls",
    "author" : "Pablo Tochez Anderson",
    "description" : "",
    "blender" : (3, 4, 0),
    "version" : (0, 0, 2),
    "location" : "",
    "warning" : "",
    "category" : "Interface"
}

import bpy
from bpy.types import Panel, Operator
from bpy.props import StringProperty, BoolProperty,EnumProperty, PointerProperty


def choose_name(node):
    if node.label:
        return node,node.label
    elif node.type == 'GROUP':
        return node,node.node_tree.name
    else:
        return node,node.name
        
def draw_nodes(self,context,layout,node_tree,external = 'space_data'):

    
    props = context.scene.control_panel_props

    row = layout.row()
    row.alignment = 'RIGHT'
    row.prop(props,'show_attributes')

    layout.use_property_split = True
    layout.use_property_decorate = False

    layout.prop(props,'sort_mode')
    layout.use_property_decorate = True


    if not node_tree:
        return

    if props.sort_mode == 'NAME':
        nodes = sorted([choose_name(node) for node in node_tree.nodes if node.get('CTRL',None) is not None],key=lambda x:x[1])
    else:
        nodes = sorted([choose_name(node) for node in node_tree.nodes if node.get('CTRL',None) is not None],key=lambda x:x[0]['CTRL'])

    if not nodes:
        return

    mat_name = external
    if external not in  ('space_data', 'compositor'):
        mat_name = external.name

    
    for node,name in nodes:
        box = layout.box()
        row = box.row(align=False)
        

        icon = 'NODE'
        if node.type == 'GROUP':
            icon = 'NODETREE'

        row.prop(node,'mute',invert_checkbox = True,text = '',icon = icon)

        row.label(text = f'{name}:')

        if props.sort_mode == 'CUSTOM':
            r2 = row.split(align = True)

            m = r2.operator('cp.change_order',text = "",icon = 'TRIA_UP')
            m.node = node.name
            m.source = mat_name
            m.direction_down = 0

            m = r2.operator('cp.change_order',text = "",icon = 'TRIA_DOWN')
            m.node = node.name
            m.source= mat_name
            m.direction_down = 1

        r = row.operator('cp.remove_input',text = "",icon = 'PANEL_CLOSE')
        r.node = node.name
        r.source = mat_name

        #DEBUG box.label(text=f"{node['CTRL']}")

        col= box.column()

        if node.mute:
            col.enabled = False

        if props.show_attributes:
            node.draw_buttons(context,col)
        
        for input in node.inputs:
            if input.is_unavailable or input.is_linked or input.type in ('SHADER'):
                continue

            col.prop(input,'default_value',text = input.name)



class CP_PT_ControlPanel3D(Panel):
    bl_label = "Node Controls"
    bl_space_type =  'VIEW_3D'
    bl_region_type = 'UI'
    bl_category  = 'Node Controls'
    #bl_options = {'DEFAULT_CLOSED'}

    
    def draw(self, context):
        layout = self.layout
        props = context.scene.control_panel_props
        
        col = layout.column()
        col.prop_tabs_enum(props, 'node_type',icon_only=False)
        row = layout.row()
        if props.node_type == 'MAT' and context.object:
            ob = context.object
            if ob.type not in ('MESH','CURVE'):
                return 
            mat = ob.material_slots

            if not any(ob and mat) or ob.type == 'GPENCIL':
                return 

            slot = ob.active_material_index
            row.template_list("MATERIAL_UL_matslots", "", ob, "material_slots", ob, "active_material_index", rows=2)

            if ob.material_slots[slot].material:
                material = ob.material_slots[slot].material
                draw_nodes(self,context,layout,material.node_tree,external=material)
        else:
            draw_nodes(self,context,layout,context.scene.node_tree,external='compositor')


class CP_PT_NodeGraphControls(Panel):
    bl_label = "Controls"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category  = 'Controls'
    
    #bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(self,context):
        return hasattr(context.space_data,'node_tree') and context.space_data.node_tree and context.space_data.node_tree.type in ('SHADER','COMPOSITING')

    
    def draw(self, context):
        layout = self.layout
        layout.operator('cp.add_input',text = "Add Nodes",icon = 'ADD')
        layout.operator('cp.remove_selected',text = "Remove Nodes",icon = 'PANEL_CLOSE')
        draw_nodes(self,context,layout,context.space_data.node_tree,external = 'space_data')


    
class CP_OT_AddInput(Operator):
    """Add Input"""
    bl_idname = "cp.add_input"
    bl_label = "Add Node"

    bl_options = {'UNDO'}

    def execute(self, context):
        space_data = context.space_data
        tree = space_data.edit_tree
        ctrl_nodes = sorted([node for node in tree.nodes if node.get('CTRL',None) is not None],key = lambda x:x['CTRL'])
        
        idx = 0

        if ctrl_nodes:
            for node in ctrl_nodes:
                node['CTRL'] = idx
                idx += 1
        

        for node in tree.nodes:
            if node.select:
                idx += 1
                node['CTRL'] = idx
                node.use_custom_color = True
                node.color = (0.7,0.46,0.0)
                

        return {'FINISHED'}

class CP_OT_RemoveInput(Operator):
    """Remove Input"""
    bl_idname = "cp.remove_input"
    bl_label = "Remove Node"

    node : StringProperty()
    source : StringProperty()

    bl_options = {'UNDO'}

    def execute(self, context):

        if self.source != 'compositor':
            if self.source == 'space_data':
                tree = context.space_data.node_tree
            else:
                mat = bpy.data.materials[self.source]
                tree = mat.node_tree
            node = tree.nodes.get(self.node)
        else:
            tree = context.scene.node_tree
        node = tree.nodes.get(self.node)
        

        if not node:
            return {'FINISHED'}

        try:
            del node['CTRL'] 
            node.use_custom_color = False
        except:
            pass


        return {'FINISHED'}
    
class CP_OT_ChangeOrder(Operator):
    """Change Order"""
    bl_idname = "cp.change_order"
    bl_label = "Move"

    node : StringProperty()
    source : StringProperty()
    direction_down : BoolProperty()

    def execute(self, context):

        tree = context.scene.node_tree
        node = tree.nodes.get(self.node)

        if not node:
            return {'FINISHED'}
        

        ctrl_nodes = sorted([node for node in tree.nodes if node.get('CTRL',None) is not None],key = lambda x:x['CTRL'])

        for i,_node in enumerate(ctrl_nodes):
            _node['CTRL'] = i

        idx = ctrl_nodes.index(node)
        
        
        try:
            if self.direction_down:
                if idx+1 < len(ctrl_nodes):
                    ctrl_nodes[idx+1]['CTRL'] =idx

                node['CTRL'] =  idx+1

                
            else:
                if idx-1 > -1:
                    ctrl_nodes[idx-1]['CTRL'] =idx
                node['CTRL'] = idx-1
        except Exception as err:
            print(err)
            pass
        


        return {'FINISHED'}
    
class CP_OT_RemoveSelected(Operator):
    """Remove Input"""
    bl_idname = "cp.remove_selected"
    bl_label = "Remove Selected Nodes"


    def execute(self, context):

        space_data = context.space_data
        tree = space_data.edit_tree

        for node in tree.nodes:
            if node.select:
                try:
                    del node['CTRL'] 
                    node.use_custom_color = False
                except:
                    pass

        return {'FINISHED'}


class CP_Props(bpy.types.PropertyGroup):
    node_type : EnumProperty(
        name = "Tyoe",
        items = (
        ("MAT","Materials","Material shader nodes"),
        ("COMP","Compositor","Compositor node graph")
        )
    )
    sort_mode : EnumProperty(
        name = "Sort Mode", 
        items = (
        ("NAME","Name","Sort by name,label or node group name"),
        ("CUSTOM","Custom","Sort by custom order")
        )
    )
    show_attributes : BoolProperty(default = True,name = "Display Node Properites")


classes = [CP_OT_AddInput,CP_OT_RemoveInput,CP_OT_RemoveSelected,CP_OT_ChangeOrder,
           CP_PT_NodeGraphControls,CP_PT_ControlPanel3D,
           CP_Props]



def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.Scene.control_panel_props = PointerProperty(type = CP_Props)

def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)


