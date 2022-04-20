export const initialState = {
  effectivePermissions: {},
}

export const reducer = (state, action) => {
  switch (action.type) {
    case 'SET_RESOURCE_EFFECTIVE_PERMISSIONS':
      return {
        ...state,
        effectivePermissions: action.data,
      }
    default:
      throw new Error(`No such action type ${action.type} exist`)
  }
}
