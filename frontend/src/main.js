import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './styles/brand-theme-v1.css'
import './styles/ui-hierarchy-v1.css'
import './styles/responsive-layout-v1.css'
import './styles/micro-interactions-v1.css'
import './styles/accessibility-v1.css'
import './styles/inpage-nav-v1.css'

const app = createApp(App)
app.use(router)
app.use(ElementPlus)
app.mount('#app')