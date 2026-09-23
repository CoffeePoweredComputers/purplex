import { createApp } from 'vue'
import './embed-style.css'
import axios from 'axios'
import EmbedApp from './EmbedApp.vue'
import { getStoredLocale, i18n, isValidLocale, setLocale } from './i18n'
import { log } from './utils/logger'
import { environment } from './services/environment'
import { installEmbedSseTokenProvider } from './services/embedService'

// Deliberately no Firebase, no vue-router, no Vuex store in this entry's
// import graph — the embed bundle must stay lean and Firebase-free until
// the LTI-based embed auth (B2, #139) lands.

axios.defaults.withCredentials = true
axios.defaults.baseURL = environment.apiUrl

const launchParams = new URLSearchParams(window.location.search)

// Provisional dev-only auth: read a mock token off the launch URL so the embed
// can be exercised against a local backend (see demo/embed/). Never honoured
// in production builds — a credential in a query string ends up in referrers
// and server logs. The LTI launch (B2, #139) hands the embed its JWT instead.
const ltiToken = environment.isDevelopment ? launchParams.get('token') : null
axios.interceptors.request.use((config) => {
  if (ltiToken) {
    config.headers.Authorization = `Bearer ${ltiToken}`
  }
  return config
})

// Route SSE token minting through the embed's own path rather than the SPA's
// Firebase exchange. Must happen before any submission opens a stream.
installEmbedSseTokenProvider()

if (environment.isDevelopment) {
  log.debug('Embed axios configured', {
    baseURL: axios.defaults.baseURL,
    hasToken: !!ltiToken,
  })
}

const app = createApp(EmbedApp).use(i18n)

const requestedLocale = launchParams.get('locale')
const locale = requestedLocale && isValidLocale(requestedLocale) ? requestedLocale : getStoredLocale()
if (locale !== 'en') {
  setLocale(locale)
}

app.mount('#embed-app')
