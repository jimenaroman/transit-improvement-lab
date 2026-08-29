import { Route, Routes } from 'react-router-dom'
import { Layout } from './components/layout/Layout'
import Home from './pages/Home'
import About from './pages/About'
import AnalyzeTrip from './pages/AnalyzeTrip'
import Research from './pages/Research'
import Methodology from './pages/Methodology'

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="about" element={<About />} />
        <Route path="analyze-trip" element={<AnalyzeTrip />} />
        <Route path="research" element={<Research />} />
        <Route path="methodology" element={<Methodology />} />
      </Route>
    </Routes>
  )
}

export default App
