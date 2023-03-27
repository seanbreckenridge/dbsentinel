import type { ReactElement } from "react";
import Navbar from "./Navbar";
import Footer from "./Footer";

interface ILayout {
  children: ReactElement;
}

export default function Layout(props: ILayout): ReactElement {
  return (
    <div className="flex min-h-screen w-full flex-col">
      <Navbar />
      <div className="flex flex-grow flex-col">{props.children}</div>
      <Footer />
    </div>
  );
}
