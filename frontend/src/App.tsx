import { DashboardLayout } from "./components/layout/DashboardLayout";
import { Header } from "./components/layout/Header";
import { DashboardPage } from "./pages/DashboardPage";

export default function App() {
  return (
    <DashboardLayout>
      <Header />
      <DashboardPage />
    </DashboardLayout>
  );
}
