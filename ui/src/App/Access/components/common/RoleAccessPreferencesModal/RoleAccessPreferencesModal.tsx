import { Dispatch, FC, useState } from 'react';
import { Dialog } from 'shared/layers/Dialog';
import { Button } from 'shared/elements/Button';
import { Select, SelectOption } from 'shared/form/Select';
import { AWS_REGIONS, AWS_SERVICES_SIMPLE } from 'core/API/constants';
import { LineBreak } from 'shared/elements/LineBreak';

interface RoleAccessPreferencesModalProps {
  role: { arn: string; inactive_tra: boolean };
  showDialog: boolean;
  setShowDialog: Dispatch<boolean>;
}

const RoleAccessPreferencesModal: FC<RoleAccessPreferencesModalProps> = ({
  role,
  showDialog,
  setShowDialog
}) => {
  const localStorageRoleSettings = 'access-settings|' + role.arn;
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
      header={''}
      size="medium"
      showCloseIcon
    >
      <div>
        <h4>User Preferences for {role.arn}</h4>
        <LineBreak />
        <label>
          Default Region:
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
        </label>
        <LineBreak />
        <label>
          Default Service:
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
        </label>
      </div>
      <LineBreak />
      <Button onClick={handleSave} color="secondary" fullWidth>
        Save
      </Button>
    </Dialog>
  );
};

export default RoleAccessPreferencesModal;
