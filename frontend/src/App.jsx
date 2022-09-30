import React from 'react'
import { BrowserRouter, Route, Switch } from 'react-router-dom'
import ProtectedDashboardRoute from './auth/ProtectedDashboardRoute'
import ProtectedRoute from './auth/ProtectedRoute'
import SelectRoles from './components/roles/SelectRoles'
import PolicyTable from './components/policy/PolicyTable'
// import ConsoleMeIdentityGroupsTable from './components/identity/IdentityGroupsTable'
// import IdentityGroupEdit from './components/identity/Group'
import ConsoleMeRequestTable from './components/request/RequestTable'
import Downloads from './components/Downloads'
import { RequestPermissions, SelfServiceWizard } from './components/SelfService'
import RequestRoleAccess from 'components/SelfService/RequestRoleAccess'
import ConsoleMeDynamicConfig from './components/DynamicConfig'
import PolicyRequestReview from './components/request/PolicyRequestsReview'
import PolicyEditor from './components/policy/PolicyEditor'
import ConsoleLogin from './components/ConsoleLogin'
import ChallengeValidator from './components/challenge/ChallengeValidator'
import CreateCloneFeature from './components/roles/CreateCloneFeature'
// import Login from './components/Login'
import Logout from './components/Logout'
import NoMatch from './components/NoMatch'
import AuthenticateModal from './components/AuthenticateModal'
// import GenerateConfig from './components/generate_config/GenerateConfig'
// import { IdentityGroupRequest } from './components/identity/GroupRequest'
// import { IdentityGroupRequestReview } from './components/identity/GroupRequestReview'
// import IdentityRequestsTable from './components/identity/IdentityRequestsTable'
// import IdentityUsersTable from './components/identity/IdentityUsersTable'
// import IdentityUserEdit from './components/identity/User'
import { Settings } from './components/settings/Settings'
import { MainProvider } from './MainProvider'
import AutomatedPermissions from 'components/AutomatedPermissions'
import EULA from './components/EULA'
import ErrorBoundary from 'components/ErrorBoundary'
import MultiFactorAuth from 'components/MultiFactorAuth'
import './App.scss'

function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <Switch>
          <ProtectedDashboardRoute
            key='roles'
            exact
            path='/'
            component={SelectRoles}
          />
          <ProtectedDashboardRoute
            key='selfservice'
            exact
            path='/selfservice'
            component={SelfServiceWizard}
          />
          <ProtectedDashboardRoute
            key='permissions-selfservice'
            exact
            path='/permissions-selfservice'
            component={RequestPermissions}
          />
          <ProtectedDashboardRoute
            key='role-selfservice'
            exact
            path='/role-selfservice'
            component={RequestRoleAccess}
          />
          <ProtectedDashboardRoute
            key='policies'
            exact
            path='/policies'
            component={PolicyTable}
          />
          {/* <ProtectedDashboardRoute
          key='groups'
          exact
          path='/groups'
          component={ConsoleMeIdentityGroupsTable}
        />
        <ProtectedDashboardRoute
          key='users'
          exact
          path='/users'
          component={IdentityUsersTable}
        />
        <ProtectedDashboardRoute
          key='group'
          path='/group/:idpName/:groupName'
          component={IdentityGroupEdit}
        />
        <ProtectedDashboardRoute
          key='user'
          path='/user/:idpName/:userName'
          component={IdentityUserEdit}
        />
        <ProtectedDashboardRoute
          key='group_request'
          path='/group_request/:idpName/:groupName'
          component={IdentityGroupRequest}
        />
        <ProtectedDashboardRoute
          key='group_request_review'
          exact
          path='/group_request/:requestId'
          component={IdentityGroupRequestReview}
        />
        <ProtectedDashboardRoute
          key='group_requests'
          exact
          path='/group_requests'
          component={IdentityRequestsTable}
        /> */}
          <ProtectedDashboardRoute
            key='review'
            exact
            path='/policies/request/:requestID'
            component={PolicyRequestReview}
          />
          <ProtectedDashboardRoute
            key='requests'
            exact
            path='/requests'
            component={ConsoleMeRequestTable}
          />
          <ProtectedDashboardRoute
            key='resource_policy'
            path='/policies/edit/:accountID/:serviceType/*/:resourceName'
            component={PolicyEditor}
          />
          <ProtectedDashboardRoute
            key='iamrole_policy'
            path='/policies/edit/:accountID/:serviceType/:resourceName'
            component={PolicyEditor}
          />
          <ProtectedDashboardRoute
            key='config'
            exact
            path='/config'
            component={ConsoleMeDynamicConfig}
          />
          {/* <ProtectedDashboardRoute
          key='generate_config'
          exact
          path='/generate_config'
          component={GenerateConfig}
        /> */}
          <ProtectedDashboardRoute
            key='role_query'
            exact
            path='/role/:roleQuery+'
            component={ConsoleLogin}
          />
          <ProtectedDashboardRoute
            key='challenge_validator'
            exact
            path='/challenge_validator/:challengeToken'
            component={ChallengeValidator}
          />
          <ProtectedDashboardRoute
            key='create_role'
            exact
            path='/create_role'
            component={CreateCloneFeature}
          />
          <ProtectedDashboardRoute
            key='settings'
            exact
            path='/settings'
            origin='/settings'
            component={Settings}
          />
          <ProtectedDashboardRoute
            key='settings'
            exact
            path='/settings/:tabName'
            origin='/settings'
            component={Settings}
          />
          <ProtectedDashboardRoute
            key='downloads'
            exact
            path='/downloads'
            component={Downloads}
          />
          <ProtectedDashboardRoute
            key='automated_permissions'
            exact
            path='/automated_permissions'
            component={AutomatedPermissions}
          />
          <ProtectedRoute key='eula' exact path='/eula' component={EULA} />
          <ProtectedRoute
            key='mfa'
            exact
            path='/mfa'
            component={MultiFactorAuth}
          />
          <ProtectedDashboardRoute
            key='logout'
            exact
            path='/logout'
            component={Logout}
          />
          {/* <Route key='login' exact path='/login' component={Login} /> */}
          <Route component={NoMatch} />
        </Switch>
        <AuthenticateModal />
      </ErrorBoundary>
    </BrowserRouter>
  )
}

const AuthWrapper = () => {
  return (
    <MainProvider>
      <App />
    </MainProvider>
  )
}

export default AuthWrapper
