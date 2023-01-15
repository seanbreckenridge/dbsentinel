import type { ReactElement } from "react";
import Navbar from "./Navbar";
import Footer from "./Footer";

interface ILayout {
  children: ReactElement;
}

export default function Layout(props: ILayout): ReactElement {
  return (
    <>
      <Navbar />
      <div className="flex min-h-screen flex-col py-2">
        {props.children}
      </div>
      <Footer />
    </>
  );
}
