import { createApp } from "vue";
import PrimeVue from "primevue/config";
import Aura from '@primevue/themes/aura';
import ToastService from 'primevue/toastservice';
import App from "./App.vue";

import "./assets/main.css";
import 'primeicons/primeicons.css'

const app = createApp(App);
app.use(PrimeVue, {
    theme: {
        preset: Aura,
        options: {
            prefix: 'p',
            darkModeSelector: 'none',
            cssLayer: false
        }
    }
});
app.use(ToastService);
app.mount("#app");
