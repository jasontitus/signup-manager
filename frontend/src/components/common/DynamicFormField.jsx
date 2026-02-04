import React from 'react';
import Input from './Input';
import Textarea from './Textarea';
import Select from './Select';

const DynamicFormField = ({ fieldConfig, value, onChange, error }) => {
  const { key, label, type, placeholder, required, options } = fieldConfig;

  switch (type) {
    case 'textarea':
      return (
        <Textarea
          label={label}
          name={key}
          value={value || ''}
          onChange={onChange}
          placeholder={placeholder}
          required={required}
          error={error}
        />
      );

    case 'select':
      return (
        <Select
          label={label}
          name={key}
          value={value || ''}
          onChange={onChange}
          options={options || []}
          required={required}
          error={error}
        />
      );

    case 'radio':
      return (
        <div className="mb-4">
          {label && (
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {label} {required && <span className="text-red-500">*</span>}
            </label>
          )}
          <div className="space-y-2">
            {options?.map((option) => (
              <label key={option.value} className="flex items-center">
                <input
                  type="radio"
                  name={key}
                  value={option.value}
                  checked={value === option.value}
                  onChange={onChange}
                  required={required}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">{option.label}</span>
              </label>
            ))}
          </div>
          {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
        </div>
      );

    case 'checkbox':
      return (
        <div className="mb-4">
          {label && (
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {label} {required && <span className="text-red-500">*</span>}
            </label>
          )}
          <div className="space-y-2">
            {options?.map((option) => (
              <label key={option.value} className="flex items-center">
                <input
                  type="checkbox"
                  name={key}
                  value={option.value}
                  checked={Array.isArray(value) && value.includes(option.value)}
                  onChange={(e) => {
                    const currentValue = Array.isArray(value) ? value : [];
                    const newValue = e.target.checked
                      ? [...currentValue, option.value]
                      : currentValue.filter((v) => v !== option.value);
                    onChange({ target: { name: key, value: newValue } });
                  }}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">{option.label}</span>
              </label>
            ))}
          </div>
          {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
        </div>
      );

    case 'email':
    case 'tel':
    case 'text':
    default:
      return (
        <Input
          type={type || 'text'}
          label={label}
          name={key}
          value={value || ''}
          onChange={onChange}
          placeholder={placeholder}
          required={required}
          error={error}
        />
      );
  }
};

export default DynamicFormField;
