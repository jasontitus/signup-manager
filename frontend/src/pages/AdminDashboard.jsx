import React, { useState, useEffect } from 'react';
import { membersAPI } from '../api/members';
import { usersAPI } from '../api/users';
import Header from '../components/layout/Header';
import MemberCard from '../components/members/MemberCard';
import Button from '../components/common/Button';
import Input from '../components/common/Input';
import Select from '../components/common/Select';
import Modal from '../components/common/Modal';

const AdminDashboard = () => {
  const [activeTab, setActiveTab] = useState('triage');
  const [members, setMembers] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [assignModalOpen, setAssignModalOpen] = useState(false);
  const [selectedMember, setSelectedMember] = useState(null);
  const [selectedVetter, setSelectedVetter] = useState('');
  const [userFormOpen, setUserFormOpen] = useState(false);
  const [reclaimingStale, setReclaimingStale] = useState(false);
  const [reclaimMessage, setReclaimMessage] = useState('');
  const [newUser, setNewUser] = useState({
    username: '',
    password: '',
    role: 'VETTER',
    full_name: '',
  });

  useEffect(() => {
    loadMembers();
    loadUsers();
  }, []);

  const loadMembers = async () => {
    setLoading(true);
    try {
      const data = await membersAPI.list();
      setMembers(data);
    } catch (err) {
      console.error('Failed to load members:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadUsers = async () => {
    try {
      const data = await usersAPI.list();
      setUsers(data);
    } catch (err) {
      console.error('Failed to load users:', err);
    }
  };

  const handleAssign = async () => {
    if (!selectedMember || !selectedVetter) return;

    try {
      await membersAPI.assign(selectedMember.id, parseInt(selectedVetter));
      setAssignModalOpen(false);
      setSelectedMember(null);
      setSelectedVetter('');
      loadMembers();
    } catch (err) {
      console.error('Failed to assign member:', err);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      await usersAPI.create(newUser);
      setUserFormOpen(false);
      setNewUser({ username: '', password: '', role: 'VETTER', full_name: '' });
      loadUsers();
    } catch (err) {
      console.error('Failed to create user:', err);
    }
  };

  const handleReclaimStale = async () => {
    setReclaimingStale(true);
    setReclaimMessage('');
    try {
      const result = await membersAPI.reclaimStaleAssignments();
      setReclaimMessage(result.message);
      if (result.reclaimed_count > 0) {
        loadMembers(); // Reload to show updated statuses
      }
    } catch (err) {
      console.error('Failed to reclaim stale assignments:', err);
      setReclaimMessage('Error reclaiming stale assignments');
    } finally {
      setReclaimingStale(false);
    }
  };

  const pendingMembers = members.filter((m) => m.status === 'PENDING');
  const assignedMembers = members.filter((m) => m.status === 'ASSIGNED');
  const vettedMembers = members.filter((m) => m.status === 'VETTED');
  const vetters = users.filter((u) => u.role === 'VETTER' && u.is_active);

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Tabs */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            {['triage', 'database', 'staff'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`${
                  activeTab === tab
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm capitalize`}
              >
                {tab}
              </button>
            ))}
          </nav>
        </div>

        {/* Triage Tab */}
        {activeTab === 'triage' && (
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              Pending Applications ({pendingMembers.length})
            </h2>
            {pendingMembers.length === 0 ? (
              <p className="text-gray-600">No pending applications</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {pendingMembers.map((member) => (
                  <div key={member.id}>
                    <MemberCard member={member} />
                    <Button
                      size="sm"
                      className="w-full mt-2"
                      onClick={() => {
                        setSelectedMember(member);
                        setAssignModalOpen(true);
                      }}
                    >
                      Assign to Vetter
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Database Tab */}
        {activeTab === 'database' && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl font-bold text-gray-900">All Members</h2>
              <Button
                onClick={handleReclaimStale}
                disabled={reclaimingStale}
                variant="secondary"
              >
                {reclaimingStale ? 'Checking...' : 'Reclaim Stale Assignments'}
              </Button>
            </div>

            {reclaimMessage && (
              <div className={`mb-4 p-3 rounded ${
                reclaimMessage.includes('Error') ? 'bg-red-100 text-red-700' :
                reclaimMessage.includes('0') ? 'bg-blue-100 text-blue-700' :
                'bg-green-100 text-green-700'
              }`}>
                {reclaimMessage}
              </div>
            )}

            <div className="mb-4 flex gap-4">
              <div className="bg-white p-4 rounded-lg shadow flex-1">
                <p className="text-sm text-gray-600">Pending</p>
                <p className="text-2xl font-bold text-yellow-600">{pendingMembers.length}</p>
              </div>
              <div className="bg-white p-4 rounded-lg shadow flex-1">
                <p className="text-sm text-gray-600">Assigned</p>
                <p className="text-2xl font-bold text-blue-600">{assignedMembers.length}</p>
              </div>
              <div className="bg-white p-4 rounded-lg shadow flex-1">
                <p className="text-sm text-gray-600">Vetted</p>
                <p className="text-2xl font-bold text-green-600">{vettedMembers.length}</p>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {members.map((member) => (
                <MemberCard key={member.id} member={member} />
              ))}
            </div>
          </div>
        )}

        {/* Staff Tab */}
        {activeTab === 'staff' && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl font-bold text-gray-900">Staff Management</h2>
              <Button onClick={() => setUserFormOpen(true)}>Add User</Button>
            </div>
            <div className="bg-white shadow rounded-lg overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Username
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Full Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Role
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {users.map((user) => (
                    <tr key={user.id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {user.username}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {user.full_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {user.role}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            user.is_active
                              ? 'bg-green-100 text-green-800'
                              : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {user.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Assign Modal */}
      <Modal
        isOpen={assignModalOpen}
        onClose={() => setAssignModalOpen(false)}
        title="Assign to Vetter"
      >
        <Select
          label="Select Vetter"
          name="vetter"
          value={selectedVetter}
          onChange={(e) => setSelectedVetter(e.target.value)}
          options={vetters.map((v) => ({ value: v.id, label: v.full_name }))}
        />
        <div className="mt-4">
          <Button onClick={handleAssign} disabled={!selectedVetter} className="w-full">
            Assign
          </Button>
        </div>
      </Modal>

      {/* User Form Modal */}
      <Modal
        isOpen={userFormOpen}
        onClose={() => setUserFormOpen(false)}
        title="Create New User"
      >
        <form onSubmit={handleCreateUser}>
          <Input
            label="Username"
            name="username"
            value={newUser.username}
            onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
            required
          />
          <Input
            label="Password"
            name="password"
            type="password"
            value={newUser.password}
            onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
            required
          />
          <Input
            label="Full Name"
            name="full_name"
            value={newUser.full_name}
            onChange={(e) => setNewUser({ ...newUser, full_name: e.target.value })}
            required
          />
          <Select
            label="Role"
            name="role"
            value={newUser.role}
            onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
            options={[
              { value: 'VETTER', label: 'Vetter' },
              { value: 'SUPER_ADMIN', label: 'Super Admin' },
            ]}
          />
          <Button type="submit" className="w-full mt-4">
            Create User
          </Button>
        </form>
      </Modal>
    </div>
  );
};

export default AdminDashboard;
