import { authStore } from '../store/auth'

// 权限常量
export const Permissions = {
  // 知识库权限
  KB_VIEW: 'kb:view',           // 查看知识库
  KB_CREATE: 'kb:create',       // 创建知识库
  KB_EDIT: 'kb:edit',          // 编辑知识库
  KB_DELETE: 'kb:delete',       // 删除知识库
  
  // 文档权限
  DOC_VIEW: 'doc:view',         // 查看文档
  DOC_CREATE: 'doc:create',     // 创建文档
  DOC_EDIT: 'doc:edit',        // 编辑文档
  DOC_DELETE: 'doc:delete',     // 删除文档
}

// 角色权限映射
const rolePermissions = {
  admin: [
    Permissions.KB_VIEW,
    Permissions.KB_CREATE,
    Permissions.KB_EDIT,
    Permissions.KB_DELETE,
    Permissions.DOC_VIEW,
    Permissions.DOC_CREATE,
    Permissions.DOC_EDIT,
    Permissions.DOC_DELETE,
  ],
  user: [
    Permissions.DOC_VIEW,  // 普通用户只有文档查看权限
  ]
}

// 权限检查函数
export function hasPermission(permission) {
  // 添加调试日志
  console.log('Checking permission:', permission)
  console.log('Current user:', authStore.user)
  console.log('Is admin:', authStore.isAdmin)
  
  // 如果用户未登录，没有任何权限
  if (!authStore.user) {
    console.log('No user logged in')
    return false
  }
  
  const role = authStore.isAdmin ? 'admin' : 'user'
  console.log('User role:', role)
  console.log('Available permissions:', rolePermissions[role])
  
  const hasPermission = rolePermissions[role].includes(permission)
  console.log('Has permission:', hasPermission)
  
  return hasPermission
}

// 权限指令
export const permissionDirective = {
  mounted(el, binding) {
    const { value } = binding
    if (!hasPermission(value)) {
      el.style.display = 'none'
    }
  },
  updated(el, binding) {
    const { value } = binding
    if (!hasPermission(value)) {
      el.style.display = 'none'
    } else {
      el.style.display = ''
    }
  }
}