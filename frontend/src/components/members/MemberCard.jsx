import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const MemberCard = ({ member, searchContext, tab }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const statusColors = {
    PENDING: 'bg-yellow-100 text-yellow-800',
    ASSIGNED: 'bg-blue-100 text-blue-800',
    VETTED: 'bg-green-100 text-green-800',
    REJECTED: 'bg-red-100 text-red-800',
  };

  return (
    <div
      onClick={() => navigate(`/members/${member.id}`, {
        state: {
          from: location.pathname,
          tab,
          searchQuery: searchContext?.query,
          resultIds: searchContext?.resultIds,
          currentIndex: searchContext?.currentIndex,
        }
      })}
      className="bg-white p-4 rounded-lg shadow hover:shadow-md transition-shadow cursor-pointer"
    >
      <div className="flex justify-between items-start mb-2">
        <h3 className="text-lg font-semibold text-gray-900">
          {member.first_name} {member.last_name}
        </h3>
        <span
          className={`px-2 py-1 text-xs font-medium rounded-full ${
            statusColors[member.status]
          }`}
        >
          {member.status}
        </span>
      </div>
      <div className="text-sm text-gray-600 space-y-1">
        <p>
          <span className="font-medium">Location:</span> {member.city}, {member.zip_code}
        </p>
        <p className="text-xs text-gray-500">
          Applied: {new Date(member.created_at).toLocaleDateString()}
        </p>
      </div>
    </div>
  );
};

export default MemberCard;
