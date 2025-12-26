'use client';

import { Platform } from '@/lib/types/order';

interface PlatformSelectorProps {
  selected: Platform;
  onChange: (platform: Platform) => void;
}

const platforms: { id: Platform; name: string; description: string; color: string }[] = [
  { id: 'shopline', name: 'SHOPLINE', description: '官方購物網站', color: 'bg-blue-500' },
  { id: 'c2c', name: 'C2C', description: '快電商平台', color: 'bg-orange-500' },
  { id: 'mixx', name: 'MIXX', description: 'MIXX 團購', color: 'bg-purple-500' },
  { id: 'aoshi', name: '奧世國際', description: '奧世國際平台', color: 'bg-pink-500' },
];

export default function PlatformSelector({ selected, onChange }: PlatformSelectorProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {platforms.map((platform) => (
        <button
          key={platform.id}
          onClick={() => onChange(platform.id)}
          className={`
            p-4 rounded-xl border-2 transition-all duration-200 text-left
            ${selected === platform.id
              ? 'border-green-500 bg-green-50 shadow-md'
              : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
            }
          `}
        >
          <div className="flex items-start gap-3">
            <div className={`w-3 h-3 rounded-full mt-1 ${platform.color}`} />
            <div>
              <p className={`font-semibold ${selected === platform.id ? 'text-green-700' : 'text-gray-800'}`}>
                {platform.name}
              </p>
              <p className="text-xs text-gray-500 mt-0.5">{platform.description}</p>
            </div>
          </div>
        </button>
      ))}
    </div>
  );
}
