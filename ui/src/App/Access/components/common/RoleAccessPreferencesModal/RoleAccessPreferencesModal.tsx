import { Dispatch, FC, useState } from 'react';
import { Dialog } from 'shared/layers/Dialog';
import { Button } from 'shared/elements/Button';
import { Select, SelectOption } from 'shared/form/Select';
import { AWS_REGIONS, AWS_SERVICES_SIMPLE } from 'core/API/constants';
import { LineBreak } from 'shared/elements/LineBreak';
import { Segment } from 'shared/layout/Segment';
import { Block } from 'shared/layout/Block';

interface RoleAccessPreferencesModalProps {
  role: { secondary_resource_id: string };
  showDialog: boolean;
  setShowDialog: Dispatch<boolean>;
}

const RoleAccessPreferencesModal: FC<RoleAccessPreferencesModalProps> = ({
  role,
  showDialog,
  setShowDialog
}) => {
  const localStorageRoleSettings =
    'access-settings|' + role.secondary_resource_id;
  const storedPreferences = JSON.parse(
    localStorage.getItem(localStorageRoleSettings) || '{}'
  );
  const [region, setRegion] = useState(storedPreferences.region || '');
  const [service, setService] = useState(storedPreferences.service || '');

  const handleSave = () => {
    localStorage.setItem(
      localStorageRoleSettings,
      JSON.stringify({ region, service })
    );
    setShowDialog(false);
  };

  return (
    <Dialog
      showDialog={showDialog}
      setShowDialog={setShowDialog}
      header="Role Preferences"
      size="medium"
      showCloseIcon
    >
      <Segment>
        <Block disableLabelPadding label="Default Region" />
        <Select
          id="region"
          name={region}
          value={region}
          onChange={value => setRegion(value)}
        >
          {AWS_REGIONS.map(region => (
            <SelectOption key={service} value={region}>
              {region}
            </SelectOption>
          ))}
        </Select>
        <LineBreak />
        <Block disableLabelPadding label="Default Service" />
        <Select
          id="service"
          name={service}
          value={service}
          onChange={value => setService(value)}
        >
          {AWS_SERVICES_SIMPLE.map(service => (
            <SelectOption key={service} value={service}>
              {service}
            </SelectOption>
          ))}
        </Select>
        <LineBreak />
        <Button size="small" onClick={handleSave} fullWidth>
          Save
        </Button>
      </Segment>
    </Dialog>
  );
};

export default RoleAccessPreferencesModal;
