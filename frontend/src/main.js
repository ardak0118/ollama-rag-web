import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { permissionDirective } from './utils/permissions'

const app = createApp(App)
app.use(router)
app.directive('permission', permissionDirective)
app.mount('#app')