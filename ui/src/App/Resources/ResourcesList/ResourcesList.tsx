import ResourcesTable from './components/ResourcesTable';
import css from './ResourcesList.module.css';

const Resources = () => {
  return (
    <div className={css.container}>
      <h3 className={css.header}>Resources</h3>
      <ResourcesTable />
    </div>
  );
};

export default Resources;
