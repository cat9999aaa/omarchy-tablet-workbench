import QtQuick
import "../../../modules/workbench-ui" as UI
Column {
    id:root;property var modelState;property var themeTokens;signal eventRequested(var event)
    spacing:themeTokens.metrics.gap
    function rows() {
        switch(modelState.destination) {
        case 'tasks':return [{id:'task',title:'示例任务 · 等待人工审阅',detail:'等待并不代表已经完成。授权操作应回到任务所属应用。'},{id:'history',title:'通知与历史',detail:'统一查看入口；本原型没有读取实际会话。'}];
        case 'device':return [{id:'light',title:modelState.observations.light.health==='unavailable'?'光线传感器 · 不支持（演示）':'光线传感器 · 120 lx（演示）',detail:'环境辅助规划中。缺失的能力不会显示为零。'},{id:'input',title:'显示与输入',detail:'复用统一组件，适配触摸、键鼠、横竖屏。'},{id:'network',title:modelState.network,detail:'示例连接状态；本原型不读取网络或定位。'}];
        case 'connections':return [{id:'phone',title:'手机与远程设备',detail:'未连接（演示）。连接成功、配对和功能验收分别记录。'},{id:'account',title:'外部账户',detail:'默认不授权。浏览器登录不代表 MAGI 获得账号权限。'}];
        default:return [{id:'appearance',title:'外观与交互',detail:'共享颜色、文字、点击区域和状态语言。原型不修改系统主题。'},{id:'privacy',title:'权限与数据',detail:'摄像头和麦克风默认关闭。会议、声纹与模型均未启用。'},{id:'extensions',title:'扩展与关于',detail:'按能力接入，不为每个插件再建一套菜单。'}];
        }
    }
    Repeater {model:root.rows()
        Rectangle {required property var modelData;width:root.width;height:rowContent.implicitHeight+root.themeTokens.metrics.paddingY*2;color:"transparent";border.color:root.themeTokens.colors.muted
            Column {id:rowContent;x:root.themeTokens.metrics.paddingX;y:root.themeTokens.metrics.paddingY;width:parent.width-x*2;spacing:root.themeTokens.metrics.gapSmall
                UI.StyledText {objectName:'capability-'+modelData.id;width:parent.width;themeTokens:root.themeTokens;text:modelData.title}
                UI.StyledText {width:parent.width;themeTokens:root.themeTokens;tone:"muted";text:modelData.detail}
            }
        }
    }
}
