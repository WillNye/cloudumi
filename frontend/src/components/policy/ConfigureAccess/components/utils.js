export const removeUserAccount = (group, userAccount) => {
  return group.filter((user) => user !== userAccount)
}

export const updateTagGroups = (data, group, defaultTag) => {
  const index = group.findIndex((elem) => elem.tag_name === defaultTag)
  if (index !== -1) {
    const newValue = group[index]
    newValue.value = newValue.value.includes(data.tag_name)
      ? newValue.value
      : [...newValue.value, data.tag_name]
    group[index] = newValue
  } else {
    group.push({
      key: defaultTag,
      value: [data.tag_name],
    })
  }
}
