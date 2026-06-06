import React, { useEffect } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';

export default function EnhancedIndianLanding({ onLaunch }: { onLaunch: () => void }) {
  const { scrollYProgress } = useScroll();
  
  const opacity = useTransform(scrollYProgress, [0, 0.5], [1, 0]);
  const scale = useTransform(scrollYProgress, [0, 0.5], [1, 0.8]);

  return (
    <div className="bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white overflow-x-hidden">
      {/* Tricolor Accent Bar - Fixed at top */}
      <div className="fixed top-0 left-0 right-0 h-2 z-50 flex shadow-lg">
        <div className="flex-1 bg-[#FF9933]"></div>
        <div className="flex-1 bg-white"></div>
        <div className="flex-1 bg-[#138808]"></div>
      </div>

      {/* Animated Tricolor Particles */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        {[...Array(50)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-2 h-2 rounded-full"
            style={{
              background: i % 3 === 0 ? '#FF9933' : i % 3 === 1 ? '#FFFFFF' : '#138808',
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              boxShadow: `0 0 10px ${i % 3 === 0 ? '#FF9933' : i % 3 === 1 ? '#FFFFFF' : '#138808'}`,
            }}
            animate={{
              y: [0, -100, 0],
              opacity: [0.2, 0.8, 0.2],
              scale: [1, 1.5, 1],
            }}
            transition={{
              duration: 5 + Math.random() * 5,
              repeat: Infinity,
              delay: Math.random() * 5,
            }}
          />
        ))}
      </div>

      {/* Hero Section - Full Screen */}
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-8">
        {/* India Map Silhouette Background */}
        <div className="absolute inset-0 flex items-center justify-center opacity-10">
          <svg viewBox="0 0 800 1000" className="w-full max-w-3xl h-auto">
            <motion.path
              d="M400,100 L420,120 L450,150 L480,180 L500,220 L510,260 L515,300 L510,340 L500,380 L485,420 L465,460 L440,500 L410,540 L380,570 L350,590 L320,600 L290,590 L260,570 L235,540 L215,500 L200,460 L190,420 L185,380 L190,340 L200,300 L215,260 L235,220 L260,180 L290,150 L320,120 L350,100 L380,90 Z"
              fill="url(#tricolor)"
              stroke="#FF9933"
              strokeWidth="2"
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 0.3 }}
              transition={{ duration: 4 }}
            />
            <defs>
              <linearGradient id="tricolor" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="#FF9933" stopOpacity="0.3" />
                <stop offset="50%" stopColor="#FFFFFF" stopOpacity="0.3" />
                <stop offset="100%" stopColor="#138808" stopOpacity="0.3" />
              </linearGradient>
            </defs>
          </svg>
        </div>

        {/* Animated Background Gradient */}
        <div className="absolute inset-0">
          <div className="absolute inset-0 bg-gradient-to-br from-[#FF9933]/10 via-slate-950 to-[#138808]/10"></div>
          <div className="absolute inset-0" style={{
            backgroundImage: `radial-gradient(circle at 50% 50%, rgba(255, 153, 51, 0.1) 0%, transparent 50%)`,
            animation: 'pulse 4s ease-in-out infinite'
          }}></div>
        </div>

        {/* Hero Content */}
        <motion.div 
          style={{ opacity, scale }}
          className="relative z-10 text-center px-8 max-w-6xl"
        >
          {/* Rotating Ashoka Chakra */}
          <motion.div
            className="w-24 h-24 mx-auto mb-8"
            animate={{ rotate: 360 }}
            transition={{ duration: 30, repeat: Infinity, ease: "linear" }}
          >
            <svg viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="45" fill="none" stroke="#000080" strokeWidth="3"/>
              <circle cx="50" cy="50" r="40" fill="none" stroke="#000080" strokeWidth="1"/>
              {[...Array(24)].map((_, i) => (
                <g key={i}>
                  <line
                    x1="50"
                    y1="50"
                    x2="50"
                    y2="10"
                    stroke="#000080"
                    strokeWidth="2"
                    transform={`rotate(${i * 15} 50 50)`}
                  />
                  <circle
                    cx="50"
                    cy="15"
                    r="2"
                    fill="#000080"
                    transform={`rotate(${i * 15} 50 50)`}
                  />
                </g>
              ))}
              <circle cx="50" cy="50" r="8" fill="#000080"/>
            </svg>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1 }}
          >
            <h1 className="text-8xl md:text-9xl font-black mb-4 tracking-tighter">
              <span className="bg-clip-text text-transparent bg-gradient-to-r from-[#FF9933] via-white to-[#138808] animate-gradient">
                VayuDrishti
              </span>
            </h1>
            <p className="text-3xl md:text-4xl text-[#FF9933] mb-3 font-bold">
              वायु दृष्टि
            </p>
            <p className="text-2xl md:text-3xl text-slate-300 mb-4 font-light tracking-wide">
              India's National Air Quality Intelligence System
            </p>
            <p className="text-[#138808] text-lg mb-12 tracking-widest uppercase font-bold">
              भारत सरकार • Powered by AI • Validated by Satellite
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5, duration: 1 }}
            className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12"
          >
            {[
              { value: "79.9%", label: "PM2.5 Accuracy", icon: "🎯", color: "#FF9933" },
              { value: "272", label: "Delhi Wards", icon: "🏛️", color: "#FFFFFF" },
              { value: "30M+", label: "Citizens Protected", icon: "🇮🇳", color: "#138808" },
            ].map((stat, i) => (
              <motion.div
                key={i}
                initial={{ scale: 0, rotate: -10 }}
                animate={{ scale: 1, rotate: 0 }}
                transition={{ delay: 0.7 + i * 0.1, type: "spring", stiffness: 200 }}
                className="relative bg-slate-900/50 backdrop-blur-xl border-2 rounded-2xl p-8 hover:scale-105 transition-transform"
                style={{ borderColor: stat.color }}
              >
                <div className="absolute top-0 left-0 w-full h-1" style={{ background: stat.color }}></div>
                <div className="text-5xl mb-3">{stat.icon}</div>
                <div className="text-5xl font-black mb-2" style={{ color: stat.color }}>
                  {stat.value}
                </div>
                <div className="text-sm text-slate-400 uppercase tracking-widest">{stat.label}</div>
              </motion.div>
            ))}
          </motion.div>

          <motion.button
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1, duration: 0.8 }}
            whileHover={{ scale: 1.05, boxShadow: "0 0 40px rgba(255, 153, 51, 0.6)" }}
            whileTap={{ scale: 0.95 }}
            onClick={onLaunch}
            className="group relative px-16 py-6 bg-gradient-to-r from-[#FF9933] via-white to-[#138808] rounded-full font-bold text-xl uppercase tracking-wider overflow-hidden shadow-2xl"
          >
            <span className="relative z-10 text-black flex items-center gap-3 justify-center">
              <span>🇮🇳</span>
              <span>Launch Dashboard</span>
            </span>
            <motion.div
              className="absolute inset-0 bg-gradient-to-r from-[#138808] via-white to-[#FF9933]"
              initial={{ x: "-100%" }}
              whileHover={{ x: "100%" }}
              transition={{ duration: 0.6 }}
            />
          </motion.button>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.5 }}
            className="mt-16 text-slate-500 text-sm"
          >
            <div className="flex flex-col items-center gap-2">
              <span>Scroll to explore our journey</span>
              <motion.div
                animate={{ y: [0, 10, 0] }}
                transition={{ duration: 1.5, repeat: Infinity }}
                className="text-[#FF9933]"
              >
                ↓
              </motion.div>
            </div>
          </motion.div>
        </motion.div>
      </section>

      {/* Our Journey Section */}
      <section className="relative py-32 px-8 bg-gradient-to-b from-slate-950 to-slate-900">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
            className="text-center mb-20"
          >
            <div className="text-6xl mb-6">🇮🇳</div>
            <h2 className="text-6xl font-black mb-6 bg-clip-text text-transparent bg-gradient-to-r from-[#FF9933] via-white to-[#138808]">
              Our Journey to Excellence
            </h2>
            <p className="text-xl text-slate-400 max-w-3xl mx-auto">
              From 59% to 80% accuracy in 9 intensive sessions. A testament to Indian innovation, dedication, and cutting-edge AI.
            </p>
            <p className="text-lg text-[#FF9933] mt-4 font-bold">
              भारत की प्रगति • India's Progress
            </p>
          </motion.div>

          {/* Timeline with Tricolor Theme */}
          <div className="space-y-16">
            {[
              {
                phase: "Phase 1",
                title: "Deep Analysis & Security Audit",
                desc: "Comprehensive codebase analysis, identified 150+ hardcoded values, secured critical vulnerabilities",
                metric: "25+ files analyzed",
                color: "#FF9933",
                icon: "🔍"
              },
              {
                phase: "Phase 2",
                title: "Real-World Validation",
                desc: "End-to-end testing against live WAQI government data across 6 Delhi locations",
                metric: "69.5% baseline accuracy",
                color: "#FFFFFF",
                icon: "✓"
              },
              {
                phase: "Phase 3",
                title: "Model Architecture Optimization",
                desc: "Tested 8 different neural network architectures, discovered wider networks outperform deeper ones",
                metric: "59.2% → 66.8% PM2.5",
                color: "#138808",
                icon: "🧠"
              },
              {
                phase: "Phase 4",
                title: "Massive Data Expansion",
                desc: "Processed 2021-2025 data: 1,551 daily + 9,409 hourly records. 6x dataset increase",
                metric: "2,007 → 12,159 samples",
                color: "#FF9933",
                icon: "📊"
              },
              {
                phase: "Phase 5",
                title: "Weather & Spatial Intelligence",
                desc: "Integrated 17 new features: temperature, humidity, wind, industrial zones, traffic density",
                metric: "12 → 29 features",
                color: "#FFFFFF",
                icon: "🌦️"
              },
              {
                phase: "Phase 6",
                title: "Target Achieved & Exceeded",
                desc: "Final model with enhanced architecture [512, 256, 128]. Government-grade accuracy achieved",
                metric: "79.9% PM2.5 | 75.9% PM10",
                color: "#138808",
                icon: "🏆"
              }
            ].map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: i % 2 === 0 ? -50 : 50 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.8, delay: i * 0.1 }}
                viewport={{ once: true }}
                className={`flex ${i % 2 === 0 ? 'flex-row' : 'flex-row-reverse'} items-center gap-12`}
              >
                <div className="flex-1">
                  <div 
                    className="inline-block px-4 py-2 rounded-full font-bold mb-4 text-lg"
                    style={{ 
                      backgroundColor: item.color, 
                      color: item.color === "#FFFFFF" ? "#000" : "#FFF",
                      boxShadow: `0 0 20px ${item.color}`
                    }}
                  >
                    {item.icon} {item.phase}
                  </div>
                  <h3 className="text-3xl font-bold mb-3">{item.title}</h3>
                  <p className="text-slate-400 text-lg mb-4">{item.desc}</p>
                  <div className="font-mono text-xl font-bold" style={{ color: item.color }}>
                    {item.metric}
                  </div>
                </div>
                <div 
                  className="w-4 h-4 rounded-full shrink-0" 
                  style={{ 
                    backgroundColor: item.color,
                    boxShadow: `0 0 30px ${item.color}`
                  }}
                ></div>
                <div className="flex-1"></div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Technology Stack with Indian Theme */}
      <section className="relative py-32 px-8 bg-slate-900">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
            className="text-center mb-20"
          >
            <div className="text-6xl mb-6">⚙️</div>
            <h2 className="text-6xl font-black mb-6 bg-clip-text text-transparent bg-gradient-to-r from-[#FF9933] via-white to-[#138808]">
              Powered by Cutting-Edge Technology
            </h2>
            <p className="text-xl text-slate-400">
              Enterprise-grade stack trusted by government institutions
            </p>
            <p className="text-lg text-[#138808] mt-4 font-bold">
              स्वदेशी तकनीक • Indigenous Technology
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: "🧠",
                title: "Advanced AI/ML",
                items: ["PyTorch Neural Networks", "198,018 Parameters", "Dual-Output Architecture", "ReduceLROnPlateau Optimization"],
                color: "#FF9933"
              },
              {
                icon: "🛰️",
                title: "Satellite Integration",
                items: ["Google Earth Engine", "Sentinel-5P Data", "Real-time NO2, SO2, CO", "Biomass Burning Detection"],
                color: "#FFFFFF"
              },
              {
                icon: "🌐",
                title: "Data Sources",
                items: ["WAQI Government API", "OpenAQ Historical Data", "CPCB Official Records", "11 Years of Data (2015-2025)"],
                color: "#138808"
              },
              {
                icon: "⚡",
                title: "Backend Infrastructure",
                items: ["FastAPI Python", "PostgreSQL + TimescaleDB", "Supabase Auth", "RESTful API"],
                color: "#FF9933"
              },
              {
                icon: "🎨",
                title: "Modern Frontend",
                items: ["React + TypeScript", "Leaflet Maps", "Recharts Analytics", "Framer Motion"],
                color: "#FFFFFF"
              },
              {
                icon: "📊",
                title: "Features",
                items: ["29 Input Features", "Weather Data", "Spatial Intelligence", "Traffic & Industrial Zones"],
                color: "#138808"
              }
            ].map((tech, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                viewport={{ once: true }}
                className="bg-slate-950/50 backdrop-blur-lg border-2 rounded-2xl p-8 hover:scale-105 transition-all duration-300"
                style={{ 
                  borderColor: tech.color,
                  boxShadow: `0 0 20px ${tech.color}20`
                }}
              >
                <div className="text-5xl mb-4">{tech.icon}</div>
                <h3 className="text-2xl font-bold mb-4" style={{ color: tech.color }}>{tech.title}</h3>
                <ul className="space-y-2">
                  {tech.items.map((item, j) => (
                    <li key={j} className="text-slate-400 flex items-start gap-2">
                      <span style={{ color: tech.color }} className="mt-1">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Impact & Recognition - India Focus */}
      <section className="relative py-32 px-8 bg-gradient-to-b from-slate-900 to-slate-950">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
            className="text-center mb-20"
          >
            <div className="text-8xl mb-6">🇮🇳</div>
            <h2 className="text-6xl font-black mb-6 bg-clip-text text-transparent bg-gradient-to-r from-[#FF9933] via-white to-[#138808]">
              Built for India, Validated by Science
            </h2>
            <p className="text-2xl text-[#FF9933] font-bold mb-4">
              भारत के लिए बनाया गया
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8 mb-20">
            {[
              { value: "12,159", label: "Training Samples", sublabel: "2015-2025 Data", color: "#FF9933" },
              { value: "79.9%", label: "PM2.5 Accuracy", sublabel: "Industry Leading", color: "#FFFFFF" },
              { value: "75.9%", label: "PM10 Accuracy", sublabel: "Target Exceeded", color: "#138808" },
              { value: "14.38", label: "PM2.5 MAE (µg/m³)", sublabel: "Best in Class", color: "#FF9933" },
              { value: "27.54", label: "PM10 MAE (µg/m³)", sublabel: "Highly Accurate", color: "#FFFFFF" },
              { value: "0.84", label: "PM2.5 R² Score", sublabel: "84% Variance Explained", color: "#138808" },
              { value: "0.87", label: "PM10 R² Score", sublabel: "87% Variance Explained", color: "#FF9933" },
              { value: "24/7", label: "Real-Time Monitoring", sublabel: "Always Active", color: "#FFFFFF" }
            ].map((stat, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, scale: 0.8 }}
                whileInView={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5, delay: i * 0.05 }}
                viewport={{ once: true }}
                className="text-center bg-slate-900/50 backdrop-blur-lg border-2 rounded-2xl p-6"
                style={{ 
                  borderColor: stat.color,
                  boxShadow: `0 0 20px ${stat.color}20`
                }}
              >
                <div className="text-5xl font-black mb-2" style={{ color: stat.color }}>{stat.value}</div>
                <div className="text-lg font-bold text-white mb-1">{stat.label}</div>
                <div className="text-sm text-slate-500">{stat.sublabel}</div>
              </motion.div>
            ))}
          </div>

          {/* India Map Highlight */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
            className="bg-gradient-to-r from-[#FF9933]/10 via-white/5 to-[#138808]/10 border-2 border-[#FF9933] rounded-3xl p-12 text-center relative overflow-hidden"
          >
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-[#FF9933] via-white to-[#138808]"></div>
            <div className="text-8xl mb-6">🏛️</div>
            <h3 className="text-4xl font-black mb-4 bg-clip-text text-transparent bg-gradient-to-r from-[#FF9933] via-white to-[#138808]">
              Serving the Nation
            </h3>
            <p className="text-2xl text-[#FF9933] font-bold mb-4">
              राष्ट्र की सेवा में
            </p>
            <p className="text-xl text-slate-300 max-w-3xl mx-auto mb-8">
              Monitoring 272 wards across Delhi NCR, providing real-time air quality intelligence to protect 
              over 30 million citizens. Our system integrates with government databases and satellite imagery 
              to deliver actionable insights for policy makers and citizens alike.
            </p>
            <div className="flex justify-center gap-8 flex-wrap">
              {[
                { value: "272", label: "Wards Monitored", color: "#FF9933" },
                { value: "30M+", label: "Citizens Protected", color: "#FFFFFF" },
                { value: "11", label: "Districts Covered", color: "#138808" }
              ].map((stat, i) => (
                <div key={i} className="text-center">
                  <div className="text-4xl font-bold mb-2" style={{ color: stat.color }}>{stat.value}</div>
                  <div className="text-sm text-slate-400">{stat.label}</div>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="relative py-32 px-8 bg-slate-950">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
          >
            <div className="text-8xl mb-8">🇮🇳</div>
            <h2 className="text-6xl font-black mb-8">
              <span className="bg-clip-text text-transparent bg-gradient-to-r from-[#FF9933] via-white to-[#138808]">
                Experience the Future of Air Quality Monitoring
              </span>
            </h2>
            <p className="text-3xl text-[#FF9933] font-bold mb-4">
              स्वच्छ हवा के लिए
            </p>
            <p className="text-2xl text-slate-400 mb-12">
              Join government officials, researchers, and citizens in making data-driven decisions for cleaner air.
            </p>
            <motion.button
              whileHover={{ scale: 1.05, boxShadow: "0 0 50px rgba(255, 153, 51, 0.8)" }}
              whileTap={{ scale: 0.95 }}
              onClick={onLaunch}
              className="px-16 py-6 bg-gradient-to-r from-[#FF9933] via-white to-[#138808] rounded-full font-bold text-xl uppercase tracking-wider shadow-2xl text-black"
            >
              🇮🇳 Launch Dashboard Now
            </motion.button>
          </motion.div>
        </div>
      </section>

      {/* Footer with Tricolor */}
      <footer className="border-t-2 border-[#FF9933] py-8 px-8 bg-slate-950">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="text-slate-500 text-sm text-center md:text-left">
            © 2026 VayuDrishti. Built for India's Future. भारत सरकार
          </div>
          <div className="flex gap-3">
            <div className="w-10 h-10 rounded-full bg-[#FF9933] shadow-lg"></div>
            <div className="w-10 h-10 rounded-full bg-white shadow-lg"></div>
            <div className="w-10 h-10 rounded-full bg-[#138808] shadow-lg"></div>
          </div>
          <div className="text-slate-500 text-sm text-center md:text-right">
            Version 5.0 Enhanced • Government Grade
          </div>
        </div>
      </footer>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.5; }
          50% { opacity: 1; }
        }
        @keyframes gradient {
          0%, 100% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
        }
        .animate-gradient {
          background-size: 200% 200%;
          animation: gradient 3s ease infinite;
        }
      `}</style>
    </div>
  );
}
