import { CombinedProviders } from './lib/CombineProviders'
import { AuthProvider } from './auth/AuthProviderDefault'
import { NotificationProvider } from './components/hooks/notifications'
import { ToastProvider } from './lib/Toast'

export const MainProvider = CombinedProviders([
  AuthProvider,
  NotificationProvider,
  ToastProvider,
])
