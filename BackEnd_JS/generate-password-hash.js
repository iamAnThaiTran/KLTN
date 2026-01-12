import bcrypt from 'bcrypt';

async function generateHashes() {
  const adminPassword = 'admin123';
  const demoPassword = 'demo123';

  const adminHash = await bcrypt.hash(adminPassword, 10);
  const demoHash = await bcrypt.hash(demoPassword, 10);

  console.log('\n=== Password Hashes Generated ===\n');
  console.log(`Admin (password: ${adminPassword}):`);
  console.log(`${adminHash}\n`);
  console.log(`Demo (password: ${demoPassword}):`);
  console.log(`${demoHash}\n`);
  console.log('Copy these hashes and update your seed-data.sql file\n');
}

generateHashes().catch(console.error);
