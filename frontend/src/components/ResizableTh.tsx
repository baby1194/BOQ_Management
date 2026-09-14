import React from "react";

interface ResizableThProps extends React.ThHTMLAttributes<HTMLTableCellElement> {
  columnKey: string;
  width?: number;
  onResizeStart: (columnKey: string, startX: number) => void;
  isRTL?: boolean;
}

const ResizableTh: React.FC<ResizableThProps> = ({
  columnKey,
  width,
  onResizeStart,
  isRTL = false,
  className = "",
  style,
  children,
  ...rest
}) => {
  return (
    <th
      {...rest}
      className={`relative ${className}`}
      style={{
        ...style,
        ...(width
          ? { width, minWidth: width, maxWidth: width }
          : {}),
      }}
    >
      {children}
      <span
        role="separator"
        aria-orientation="vertical"
        onPointerDown={(event) => {
          event.preventDefault();
          event.stopPropagation();
          onResizeStart(columnKey, event.clientX);
        }}
        className={`absolute top-0 bottom-0 w-1.5 cursor-col-resize hover:bg-blue-400/70 z-20 ${
          isRTL ? "left-0" : "right-0"
        }`}
      />
    </th>
  );
};

export default ResizableTh;
