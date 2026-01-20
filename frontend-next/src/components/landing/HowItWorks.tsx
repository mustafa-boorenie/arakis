'use client';

const STEPS = [
  {
    number: '01',
    title: 'Create an Account',
    description: 'Sign up in seconds and set up your workspace. Invite collaborators, choose your research context, and configure permissions.',
    highlight: 'Condense Hours into Minutes',
    imageAlt: 'Account creation screen',
  },
  {
    number: '02',
    title: 'Start Your Research',
    description: 'Create a new project and define your research question, criteria, and methodology. Select sources and connect databases to begin.',
    imageAlt: 'Research setup interface',
  },
  {
    number: '03',
    title: 'AI Process Evidence',
    description: 'ARAKIS analyzes matches, extracts data, assesses bias, and synthesizes findings. All results undergo built-in validation to ensure accuracy and transparency.',
    imageAlt: 'AI processing visualization',
  },
  {
    number: '04',
    title: 'Edit & Finalize',
    description: 'Review AI-generated outputs, refine conclusions, and make final edits. Export polished manuscripts, tables, and reports—ready for submission.',
    imageAlt: 'Manuscript editor',
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="py-20 px-4 sm:px-6 lg:px-8 bg-gray-50">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-gray-900">
            How{' '}
            <span className="bg-gradient-to-r from-purple-600 to-purple-800 bg-clip-text text-transparent">
              Arakis.AI
            </span>{' '}
            Works
          </h2>
          <p className="mt-4 text-lg text-gray-600 max-w-2xl mx-auto">
            Follow a simple, structured workflow, powered by AI, guided by research best practices, and built for complete transparency.
          </p>
        </div>

        {/* Steps */}
        <div className="space-y-16 lg:space-y-24">
          {STEPS.map((step, index) => (
            <div
              key={step.number}
              className={`flex flex-col ${
                index % 2 === 0 ? 'lg:flex-row' : 'lg:flex-row-reverse'
              } gap-8 lg:gap-16 items-center`}
            >
              {/* Content */}
              <div className="flex-1 max-w-xl">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 bg-purple-600 rounded-xl flex items-center justify-center">
                    <span className="text-white font-bold">{step.number}</span>
                  </div>
                  <h3 className="text-2xl font-bold text-gray-900">{step.title}</h3>
                </div>
                <p className="text-gray-600 leading-relaxed">
                  {step.description}
                </p>
                {step.highlight && (
                  <p className="mt-4 text-purple-600 font-medium">
                    {step.highlight}
                  </p>
                )}
              </div>

              {/* Image Placeholder */}
              <div className="flex-1 w-full max-w-xl">
                <div className="bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden">
                  {/* Browser Chrome */}
                  <div className="bg-gray-100 px-4 py-2 flex items-center gap-2 border-b border-gray-200">
                    <div className="flex gap-1.5">
                      <div className="w-2.5 h-2.5 rounded-full bg-red-400" />
                      <div className="w-2.5 h-2.5 rounded-full bg-yellow-400" />
                      <div className="w-2.5 h-2.5 rounded-full bg-green-400" />
                    </div>
                  </div>

                  {/* Content Area */}
                  <div className="p-6 bg-gradient-to-br from-gray-50 to-white min-h-[200px] flex items-center justify-center">
                    <div className="text-center">
                      {/* Placeholder graphic based on step */}
                      {step.number === '01' && (
                        <div className="space-y-3">
                          <div className="w-16 h-16 bg-purple-100 rounded-full mx-auto flex items-center justify-center">
                            <div className="w-8 h-8 bg-purple-200 rounded-full" />
                          </div>
                          <div className="h-3 bg-gray-200 rounded w-32 mx-auto" />
                          <div className="h-8 bg-purple-100 rounded-lg w-40 mx-auto" />
                        </div>
                      )}
                      {step.number === '02' && (
                        <div className="space-y-3 w-full max-w-xs mx-auto">
                          <div className="h-4 bg-gray-200 rounded w-3/4 mx-auto" />
                          <div className="h-10 bg-purple-50 rounded-lg border border-purple-100" />
                          <div className="flex gap-2 justify-center">
                            <div className="h-6 bg-gray-100 rounded-full w-16" />
                            <div className="h-6 bg-gray-100 rounded-full w-20" />
                          </div>
                        </div>
                      )}
                      {step.number === '03' && (
                        <div className="space-y-2 w-full max-w-xs mx-auto">
                          <div className="flex items-center gap-2">
                            <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse" />
                            <div className="h-3 bg-gray-200 rounded flex-1" />
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="w-3 h-3 bg-green-400 rounded-full" />
                            <div className="h-3 bg-gray-200 rounded flex-1" />
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="w-3 h-3 bg-purple-400 rounded-full animate-pulse" />
                            <div className="h-3 bg-purple-100 rounded flex-1" />
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="w-3 h-3 bg-gray-300 rounded-full" />
                            <div className="h-3 bg-gray-100 rounded flex-1" />
                          </div>
                        </div>
                      )}
                      {step.number === '04' && (
                        <div className="space-y-2 w-full max-w-xs mx-auto text-left">
                          <div className="h-5 bg-gray-300 rounded w-2/3" />
                          <div className="h-3 bg-gray-200 rounded w-full" />
                          <div className="h-3 bg-gray-200 rounded w-5/6" />
                          <div className="h-3 bg-gray-200 rounded w-4/5" />
                          <div className="mt-4 flex gap-2">
                            <div className="h-8 bg-purple-600 rounded w-20" />
                            <div className="h-8 bg-gray-200 rounded w-16" />
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
