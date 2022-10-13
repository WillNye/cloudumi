export const formatSearchResults = (data, value) =>
  data
    .map((group, idx) => {
      return {
        id: idx,
        title: group.GroupName,
        name: group.GroupName,
        description: group.Description || '',
      }
    })
    .filter(({ name, description }) => {
      const lowercaseName = name.toLocaleLowerCase()
      const lowercaseDescription = description.toLocaleLowerCase()
      return (
        lowercaseName.includes(value) || lowercaseDescription.includes(value)
      )
    })
