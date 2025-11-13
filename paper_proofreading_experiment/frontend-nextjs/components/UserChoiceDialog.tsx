'use client';

import { X } from 'lucide-react';

interface UserChoiceDialogProps {
  message: string;
  choices: string[];
  onChoice: (choice: string) => void;
  onClose: () => void;
}

export default function UserChoiceDialog({
  message,
  choices,
  onChoice,
  onClose,
}: UserChoiceDialogProps) {
  const handleChoice = (choice: string) => {
    onChoice(choice);
    onClose();
  };

  const getChoiceLabel = (choice: string): string => {
    switch (choice) {
      case 'Y':
        return 'はい (Y)';
      case 'N':
        return 'いいえ (N)';
      default:
        return choice;
    }
  };

  const getChoiceColor = (choice: string): string => {
    switch (choice) {
      case 'Y':
        return 'bg-green-600 hover:bg-green-700';
      case 'N':
        return 'bg-red-600 hover:bg-red-700';
      default:
        return 'bg-blue-600 hover:bg-blue-700';
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h3 className="text-xl font-bold text-gray-900">確認</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="p-6">
          <p className="text-gray-900 text-lg mb-6">{message}</p>

          <div className="flex space-x-3">
            {choices.map((choice) => (
              <button
                key={choice}
                onClick={() => handleChoice(choice)}
                className={`flex-1 px-4 py-3 text-white rounded-lg transition-colors ${getChoiceColor(
                  choice
                )}`}
              >
                {getChoiceLabel(choice)}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
