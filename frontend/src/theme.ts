import type { ThemeConfig } from 'antd'

/**
 * 全局设计体系 —— 施工企业运营托管数字化系统
 * 以「沉稳蓝 + 工程感」为基调，统一圆角、阴影、间距与控件质感，
 * 保证全站视觉一致、专业、大气。
 */

// 品牌色板
export const brand = {
  primary: '#1668dc',
  primaryDeep: '#0b3d91',
  cyan: '#13c2c2',
  // 侧边栏深色导航
  siderTop: '#0b1f3a',
  siderBottom: '#102a52',
  // 主渐变（按钮 / Logo / 强调）
  gradient: 'linear-gradient(135deg, #1668dc 0%, #0b3d91 100%)',
  gradientCyan: 'linear-gradient(135deg, #1668dc 0%, #13c2c2 100%)',
}

const theme: ThemeConfig = {
  token: {
    colorPrimary: brand.primary,
    colorInfo: brand.primary,
    colorLink: brand.primary,
    colorSuccess: '#16a34a',
    colorWarning: '#f59e0b',
    colorError: '#ef4444',
    borderRadius: 10,
    fontSize: 14,
    fontFamily:
      "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif",
    colorBgLayout: '#f4f6fb',
    colorTextHeading: '#0f172a',
    colorText: '#1f2937',
    boxShadowSecondary:
      '0 6px 16px -8px rgba(15, 23, 42, 0.12), 0 9px 28px -10px rgba(15, 23, 42, 0.08)',
    wireframe: false,
  },
  components: {
    Layout: {
      headerBg: '#ffffff',
      headerHeight: 64,
      headerPadding: '0 24px',
      bodyBg: '#f4f6fb',
      siderBg: 'transparent',
      triggerBg: 'rgba(255,255,255,0.08)',
    },
    Menu: {
      darkItemBg: 'transparent',
      darkSubMenuItemBg: 'transparent',
      darkItemSelectedBg: 'rgba(22, 104, 220, 0.92)',
      darkItemHoverBg: 'rgba(255,255,255,0.08)',
      darkItemColor: 'rgba(255,255,255,0.72)',
      darkItemSelectedColor: '#ffffff',
      itemHeight: 44,
      itemMarginInline: 10,
      itemBorderRadius: 8,
      iconSize: 16,
    },
    Card: {
      borderRadiusLG: 14,
      paddingLG: 20,
      headerFontSize: 15,
      boxShadowTertiary:
        '0 1px 2px rgba(15, 23, 42, 0.04), 0 4px 12px rgba(15, 23, 42, 0.05)',
    },
    Table: {
      headerBg: '#f7f9fc',
      headerColor: '#475569',
      headerSplitColor: 'transparent',
      borderColor: '#eef2f7',
      rowHoverBg: '#f4f8ff',
      cellPaddingBlock: 12,
    },
    Button: {
      controlHeight: 36,
      borderRadius: 8,
      fontWeight: 500,
      primaryShadow: '0 4px 12px rgba(22, 104, 220, 0.28)',
    },
    Input: { controlHeight: 36, borderRadius: 8 },
    Select: { controlHeight: 36, borderRadius: 8 },
    Statistic: { titleFontSize: 13 },
    Tag: { borderRadiusSM: 6 },
    Segmented: { borderRadius: 8 },
  },
}

export default theme
